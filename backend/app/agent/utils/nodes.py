"""普通节点工厂 + 路由函数"""
from typing import Dict, List
import time
import json

from langgraph.graph import END
from langgraph.types import interrupt
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from app.core.logging import get_logger
from app.agent.state import AgentState, _content_blocks_to_str
from app.agent.context_engine import MAX_CONTEXT_CHARS
from app.agent.utils.common import (
    ErrorContract, CircuitBreaker, _circuit_breaker, MAX_MESSAGE_WINDOW,
    _content_to_str, _build_message_dicts,
    _trim_messages, _format_tool_result_json,
)
from app.agent.utils.goal_helpers import _parse_goal_subtasks, _validate_goal_definition, _build_goal_progress_text, _get_next_pending_subtask

logger = get_logger(__name__)


def _make_model_selector_node(model_selector):
    """模型选择节点（v5.3 — ML 模型路由）

    流程：390维特征提取 → LightGBM 推理 → 6层后处理
    输出：route_class/tier/selected_model/thinking_mode/prompt_policy/prompt_hint
    """
    async def model_selector_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()
        t0 = time.time()

        if not model_selector:
            writer({"step": "model_select", "status": "skipped", "message": "模型路由未初始化"})
            return {"selected_model": "", "routing_confidence": 0.0, "routing_reason": "no_selector"}

        query = _extract_last_message(state)
        if not query or not query.strip():
            writer({"step": "model_select", "status": "skipped", "message": "空消息，跳过路由"})
            return {"selected_model": "", "routing_confidence": 0.0, "routing_reason": "empty"}

        # 提取对话历史
        history = []
        for msg in (state.get("messages") or [])[-12:]:
            if isinstance(msg, dict):
                history.append(msg)
            elif hasattr(msg, "role") and hasattr(msg, "content"):
                history.append({"role": msg.role, "content": str(msg.content)})

        # 路由分类（ML 或规则降级）
        decision = model_selector.classify(query, history=history if history else None)
        elapsed = time.time() - t0

        writer({
            "step": "model_select",
            "status": "done",
            "message": f"模型路由: {decision.selected_model} ({decision.route_class}/{decision.tier}, {decision.reason}, {elapsed*1000:.0f}ms)",
            "selected_model": decision.selected_model,
            "route_class": decision.route_class,
            "tier": decision.tier,
            "thinking_mode": decision.thinking_mode,
            "prompt_policy": decision.prompt_policy,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "elapsed_ms": int(elapsed * 1000),
        })

        logger.info(
            f"[model_selector] model={decision.selected_model} route={decision.route_class} "
            f"tier={decision.tier} thinking={decision.thinking_mode} policy={decision.prompt_policy} "
            f"confidence={decision.confidence:.2f} reason={decision.reason} elapsed={elapsed:.3f}s"
        )

        return {
            "selected_model": decision.selected_model,
            "routing_confidence": decision.confidence,
            "routing_reason": decision.reason,
            "route_class": decision.route_class,
            "tier": decision.tier,
            "thinking_mode": decision.thinking_mode,
            "prompt_policy": decision.prompt_policy,
            "prompt_hint": decision.prompt_hint,
            "difficulty_score": decision.difficulty_score,
            "routing_probabilities": decision.probabilities,
            "routing_flags": decision.flags,
        }

    return model_selector_node


def _make_intent_router(intent_router):
    async def intent_router_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        if not intent_router:
            writer({"step": "intent", "status": "skipped", "message": "意图路由未初始化"})
            return {"intent": None}

        t0 = time.time()
        writer({"step": "intent", "status": "searching", "message": "正在分析意图..."})
        query = _extract_last_message(state)
        if not query or not query.strip():
            writer({"step": "intent", "status": "skipped", "message": "空消息，跳过意图路由"})
            return {"intent": None}

        try:
            intent = await intent_router.route(query, user_id=state.get("user_id", 0))
        except Exception as e:
            logger.warning(f"[intent_router] 路由失败（降级走 Agent）: {e}")
            intent = None

        elapsed = time.time() - t0
        logger.info(f"[intent_router] hit={intent is not None} elapsed={elapsed:.3f}s")

        if intent and intent.get("cached_answer"):
            writer({"step": "intent", "status": "done", "message": f"缓存命中 ({elapsed:.1f}s)", "elapsed_ms": int(elapsed * 1000)})
            return {
                "intent": intent,
                "final_answer": intent["cached_answer"],
                "skill_answer": intent["cached_answer"],
                "messages": [AIMessage(content=intent["cached_answer"])],
            }

        if intent:
            name = intent.get("intent_name", "unknown")
            score = intent.get("score", 0)
            writer({"step": "intent", "status": "done", "message": f"命中「{name}」(置信度 {score:.0%})", "intent": name, "score": score, "elapsed_ms": int(elapsed * 1000)})
        else:
            writer({"step": "intent", "status": "done", "message": f"未命中，走通用对话 ({elapsed:.1f}s)", "elapsed_ms": int(elapsed * 1000)})

        return {"intent": intent}

    return intent_router_node


def _make_skill_executor_node(skill_executor, context_engine=None, memory_manager=None):
    async def skill_executor_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        if not skill_executor or not state.get("intent"):
            return {"skill_answer": None, "final_answer": None}

        intent = state["intent"]
        target = intent.get("target_module", "")
        if not target or target == "cache":
            return {"skill_answer": None, "final_answer": None}

        writer({"step": "skill", "status": "executing", "message": f"正在执行技能「{target}」..."})
        t0 = time.time()
        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                answer = await skill_executor.execute(
                    db=db,
                    skill_name=target,
                    user_message=_extract_last_message(state),
                    messages=_build_message_dicts(state),
                    provider_id=state.get("provider_id"),
                    model_name=state.get("model_name", ""),
                    context_engine=context_engine,
                    memory_manager=memory_manager,
                )
        except Exception as e:
            logger.error(f"[skill_executor] 技能 '{target}' 执行失败: {e}", exc_info=True)
            answer = None

        elapsed = time.time() - t0
        logger.info(f"[skill_executor] skill={target} elapsed={elapsed:.2f}s success={answer is not None}")

        if answer:
            writer({"step": "skill", "status": "done", "message": f"技能「{target}」执行完成 ({elapsed:.1f}s)", "elapsed_ms": int(elapsed * 1000)})
            return {
                "skill_answer": answer,
                "final_answer": answer,
                "messages": [AIMessage(content=answer)],
            }
        writer({"step": "skill", "status": "error", "message": f"技能「{target}」执行失败"})
        return {"skill_answer": None, "final_answer": None}

    return skill_executor_node


def _make_context_builder(context_engine, memory_manager, tool_registry=None):
    async def context_builder_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        t0 = time.time()
        query = _extract_last_message(state)
        memory_context = None  # 记忆元数据，默认无

        # ── B+C: 根据 intent 动态选择工具（存储工具名，非 Tool 对象）──
        writer({"step": "tools", "status": "searching", "message": "正在选择工具..."})
        selected_tool_names = _select_tool_names_for_intent(state, tool_registry)
        tool_count = len(selected_tool_names)
        logger.info(f"[context_builder] 动态工具选择: intent={(state.get('intent') or {}).get('intent_name', 'none')} tools={tool_count}")
        writer({"step": "tools", "status": "done", "message": f"已选 {tool_count} 个工具", "count": tool_count})

        if context_engine:
            try:
                # ── Query Rewriting（RAG 检索前改写口语化查询）──
                writer({"step": "rewrite", "status": "searching", "message": "正在改写查询..."})
                messages_for_rewrite = _build_message_dicts(state)
                rewritten_query = await context_engine.rewrite_query(
                    user_query=query,
                    conversation_history=messages_for_rewrite[:-1],  # 排除当前消息
                )
                writer({"step": "rewrite", "status": "done", "message": "查询改写完成"})

                # 传递选中的工具名摘要给 context_engine
                tool_summaries = None
                if tool_registry and selected_tool_names:
                    tool_summaries = []
                    for name in selected_tool_names:
                        tdef = tool_registry.get(name)
                        if tdef:
                            tool_summaries.append({"name": tdef.name, "description": tdef.description})

                writer({"step": "context", "status": "searching", "message": "正在组装上下文（记忆 + RAG）..."})
                result = await context_engine.assemble(
                    user_id=state.get("user_id", 0),
                    conversation_id=state.get("conversation_id", 0),
                    user_message=rewritten_query,  # 用改写后的查询
                    intent=state.get("intent"),
                    tools=tool_summaries or (context_engine.get_tool_summaries() if context_engine else None),
                )
                system_prompt = result.system_prompt

                # ── Context 压缩（超长时自动压缩）──
                if result.total_chars > MAX_CONTEXT_CHARS:
                    system_prompt = await context_engine.compress_context(
                        system_prompt, target_chars=MAX_CONTEXT_CHARS
                    )

                logger.info(f"[context_builder] sources={result.sources_used} chars={result.total_chars} elapsed={time.time()-t0:.2f}s")

                elapsed = time.time() - t0
                sources = result.sources_used or []
                source_desc = "、".join(sources) if sources else "无"
                writer({"step": "context", "status": "done", "message": f"上下文就绪 ({source_desc}, {result.total_chars}字, {elapsed:.1f}s)", "sources": sources, "chars": result.total_chars, "elapsed_ms": int(elapsed * 1000)})

                # 记忆元数据 → State（供 memory_saver / evaluator 消费）
                if result.memory_count > 0:
                    avg_score = sum(result.memory_scores) / len(result.memory_scores) if result.memory_scores else 0
                    memory_context = {
                        "ids": result.memory_ids,
                        "scores": result.memory_scores,
                        "count": result.memory_count,
                        "avg_score": round(avg_score, 3),
                    }
                    logger.info(f"[context_builder] 记忆元数据: count={result.memory_count} avg_score={avg_score:.3f}")
            except Exception as e:
                logger.warning(f"[context_engine] 组装失败，降级为简单提示: {e}")
                system_prompt = "你是一个智能助手，能够使用工具回答用户问题。请用中文回答。"
        else:
            system_prompt = "你是一个智能助手，能够使用工具回答用户问题。请用中文回答。"
            if memory_manager and query:
                try:
                    memory_context = await memory_manager.search(query=query, user_id=state.get("user_id", 0), limit=5)
                    if memory_context:
                        system_prompt += f"\n\n【相关记忆】\n{memory_context}"
                except Exception as e:
                    logger.warning(f"[context_builder] 记忆检索失败（降级跳过）: {e}")

        # ── P0: 跨线程记忆检索（MySQL CrossThreadMemory）──
        try:
            from app.core.database import AsyncSessionLocal
            from app.repository.cross_thread_memory_repo import CrossThreadMemoryRepository
            async with AsyncSessionLocal() as mem_db:
                repo = CrossThreadMemoryRepository()
                items = await repo.find_by_user(
                    mem_db, user_id=state.get("user_id", 0),
                    namespace="conversations", limit=3,
                )
                if items:
                    store_context = "\n".join(
                        f"- {m.content.get('query', '')[:80]}: {m.content.get('answer', '')[:120]}"
                        for m in items if m.content.get('answer')
                    )
                    if store_context:
                        system_prompt += f"\n\n【历史对话参考】\n{store_context}"
                        logger.info(f"[context_builder] 跨线程记忆命中: {len(items)} 条")
        except Exception as e:
            logger.debug(f"[context_builder] 跨线程记忆检索跳过: {e}")

        # ── v5.2: 主动回忆注入（高价值、低访问的记忆提醒）──
        if memory_manager:
            try:
                proactive_text = await memory_manager.proactive_recall(
                    user_id=state.get("user_id", 0),
                    max_items=3,
                )
                if proactive_text:
                    system_prompt += proactive_text
                    logger.info("[context_builder] 主动回忆已注入")
            except Exception as e:
                logger.debug(f"[context_builder] 主动回忆跳过: {e}")

        return {
            "system_prompt": system_prompt,
            "context": system_prompt,
            "memory_context": memory_context,
            "selected_tools": selected_tool_names,
        }

    return context_builder_node


def _make_llm_caller(llm, tool_registry=None, model_selector=None):
    async def llm_call_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        t0 = time.time()

        # ── 按路由结果动态选择 LLM ──
        selected_model = state.get("selected_model") or ""
        if model_selector and selected_model:
            current_base_llm = model_selector.get_llm(selected_model)
            model_label = selected_model
        else:
            current_base_llm = llm
            model_label = state.get("model_name") or "default"

        # 路由信息
        thinking_mode = state.get("thinking_mode", "")
        prompt_policy = state.get("prompt_policy", "")
        prompt_hint = state.get("prompt_hint", "")
        route_class = state.get("route_class", "")
        tier = state.get("tier", "")

        writer({"step": "llm", "status": "calling", "message": f"正在生成回答... (模型: {model_label}, 路由: {route_class}/{tier}, 思考: {thinking_mode})"})

        system_prompt = state.get("system_prompt") or state.get("context") or \
            "你是一个智能助手，能够使用工具回答用户问题。请用中文回答。"

        # 注入路由提示
        if prompt_hint:
            system_prompt = f"{system_prompt}\n\n【指令】{prompt_hint}"

        # ── Goal 模式：注入任务拆解与执行指令 ──
        # 规划执行分离：第0轮只输出计划，后续轮强制使用工具执行
        if state.get("goal_mode"):
            goal_def = state.get("goal_definition", "")
            iterations = state.get("goal_iterations", 0)
            history = state.get("goal_history", [])
            current_plan = state.get("goal_current_plan", "")
            goal_subtasks = state.get("goal_subtasks", [])

            if iterations == 0:
                # 输入校验
                is_valid, validation_error = _validate_goal_definition(goal_def)
                if not is_valid:
                    writer({"step": "goal_validation", "status": "error",
                            "message": f"目标校验失败: {validation_error}"})
                    return {"final_answer": f"❌ 目标校验失败: {validation_error}", "is_error": True}

                # ── 第0轮：规划阶段（结构化输出，100% 可靠解析）──
                # 不注入 system_prompt，直接用干净的 LLM 调用
                from app.agent.structured_schemas import SubtaskPlan
                plan_llm = llm.with_structured_output(SubtaskPlan)
                plan_prompt = f"""分析以下目标，制定一个分步执行计划。

## 目标
{goal_def}

## 规划原则
1. 不要添加任何多余的步骤 — 每个步骤都必须是达成目标的必要条件
2. 确保每个步骤包含所需的所有信息 — 不要跳过步骤
3. 最后一个步骤的结果应为最终答案
4. 每个步骤必须是可通过一次工具调用完成的原子操作
5. 每个步骤必须有明确的成功标准
6. 子任务数量控制在 3-8 个

## 依赖规则
- 如果任务 B 需要任务 A 的结果才能开始，设置 dependencies: [A的id]
- 无依赖的任务可以并行执行
- id 从 1 开始递增"""
                try:
                    plan_result = await plan_llm.ainvoke([HumanMessage(content=plan_prompt)])
                    # 转为 state 格式
                    parsed = [{
                        "id": st.id,
                        "title": st.title,
                        "description": st.description,
                        "status": "pending",
                        "progress": 0,
                        "retry_count": 0,
                        "dependencies": st.dependencies,
                    } for st in plan_result.subtasks]
                    if parsed:
                        writer({"step": "goal_subtasks", "status": "done",
                                "message": f"任务拆解完成: {len(parsed)} 个子任务", "subtasks": parsed})
                        return {
                            "goal_subtasks": parsed,
                            "final_answer": f"[目标拆解] {len(parsed)} 个子任务已规划",
                        }
                    else:
                        return {"final_answer": "❌ 规划失败：未能生成有效计划", "is_error": True, "goal_status": "failed"}
                except Exception as e:
                    logger.error(f"[llm_call] 结构化规划失败: {e}")
                    return {"final_answer": f"❌ 规划失败: {e}", "is_error": True, "goal_status": "failed"}
            else:
                # ── 后续轮：执行阶段（强制使用工具，禁止跳过）──
                # 找出未完成的子任务
                pending_tasks = []
                done_tasks = []
                for st in goal_subtasks:
                    if st.get("status") == "done":
                        done_tasks.append(st)
                    else:
                        pending_tasks.append(st)

                pending_text = ""
                for pt in pending_tasks:
                    deps = pt.get("dependencies", [])
                    dep_str = f" -> 依赖: {','.join(str(d) for d in deps)}" if deps else ""
                    pending_text += f"• [{pt.get('title', '')}] - [pending]{dep_str}\n"

                done_text = ""
                for dt in done_tasks:
                    done_text += f"• [{dt.get('title', '')}] - [done] (100%)\n"

                history_text = ""
                if history:
                    last = history[-1]
                    history_text = f"""上一轮执行结果：
- 评估：{last.get('evaluation', '无')}
- 建议：{last.get('suggestion', '无')}"""

                # ── P0 fix: 构建进度文本 & 当前任务文本 ──
                progress_text = _build_goal_progress_text(goal_subtasks)
                current_task = _get_next_pending_subtask(goal_subtasks)
                current_task_text = f"**当前子任务**: {current_task['title']}" if current_task else "所有子任务已完成"

                # ── Evaluator 反馈注入（重试时）──
                eval_feedback_text = ""
                if current_task and current_task.get("last_eval_feedback"):
                    eval_feedback_text = f"\n\n⚠️ 上次执行质量不合格，原因：{current_task['last_eval_feedback']}\n请针对以上问题改进执行方式。"

                # Self-Healing: 注入自愈记忆到 prompt
                healing_context = ""
                try:
                    from app.agent.self_healing import get_healing_memory
                    healing_context = await get_healing_memory().to_prompt_context(
                        user_id=state.get("user_id", 0),
                        goal_id=str(state.get("conversation_id", 0)),
                    )
                except Exception as e:
                    logger.debug(f"[llm_call] 自愈记忆注入跳过: {e}")

                # ── Working Memory: 前序任务结果累积 ──
                working_memory_text = ""
                goal_working_memory = state.get("goal_working_memory") or []
                if goal_working_memory:
                    wm_lines = ["\n## 前序任务结果（可直接引用，不要重复执行）"]
                    for wm in goal_working_memory:
                        status_icon = "✅" if wm.get("success") else "❌"
                        wm_lines.append(f"{status_icon} 任务{wm.get('task_id', '?')}「{wm.get('title', '')}」: {wm.get('result_summary', '无')}")
                    working_memory_text = "\n".join(wm_lines)

                system_prompt = f"""{system_prompt}

══════════════════════════════════════════════════
【目标驱动模式 — 第{iterations}轮：执行】
══════════════════════════════════════════════════

## 目标
{goal_def}

## 当前进度
{progress_text if progress_text else "尚未开始"}
{current_task_text}
{history_text}
{working_memory_text}

## 执行方式（ReAct 模式）
对当前子任务，按以下步骤执行：
Thought: 分析需要调用什么工具，为什么
Action: **必须调用工具**获取真实数据（禁止跳过此步骤）
Observation: 检查工具返回结果
Answer: 基于工具结果输出该子任务的成果

## 核心规则
1. **必须调用工具** — 有可用工具时必须调用，禁止只说「我来帮你」而不执行。没有工具时基于已有知识直接回答
2. **只做一件事** — 只执行上面列出的当前子任务，不要跳到其他任务
3. **只输出当前任务结果** — 不要输出其他子任务的内容或预览
4. **禁止承诺性回复** — 不要说「我来帮你查」「让我看看」，直接执行
5. **完成后标记** — 输出: • [子任务描述] - [done] (100%)

{eval_feedback_text}
{healing_context}"""


            # 注意：iterations == 0 的 prompt 已在上方行 535-571 定义，此处不再重复


        lc_messages = [SystemMessage(content=system_prompt)]

        # ── Auto-Compaction（压缩旧历史，仅首次检查）──────
        raw_messages = state["messages"]
        if len(raw_messages) > MAX_MESSAGE_WINDOW and not state.get("is_compacted"):
            try:
                from app.agent.compaction import maybe_compact
                raw_messages = await maybe_compact(
                    messages=[{"role": getattr(m, "role", m.get("role", "user")), "content": _content_to_str(getattr(m, "content", m.get("content", "")))} for m in raw_messages],
                    llm_client=llm,
                    user_id=state.get("user_id", 0),
                    conversation_id=state.get("conversation_id", 0),
                )
                _compacted = True
            except Exception as e:
                logger.warning(f"[llm_call] compaction 失败，降级为窗口裁剪: {e}")
                raw_messages = _trim_messages(raw_messages, MAX_MESSAGE_WINDOW)
                _compacted = True
        else:
            raw_messages = _trim_messages(raw_messages, MAX_MESSAGE_WINDOW)
            _compacted = state.get("is_compacted", False)

        for m in raw_messages:
            if isinstance(m, dict):
                role, content = m.get("role", "user"), _content_to_str(m.get("content", ""))
            else:
                role, content = getattr(m, "role", "user"), _content_to_str(getattr(m, "content", ""))

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                tool_call_id = getattr(m, "tool_call_id", "") if not isinstance(m, dict) else m.get("tool_call_id", "")
                lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id or "unknown"))
            else:
                lc_messages.append(HumanMessage(content=content))

        # ── B+C: 动态绑定工具 ──
        selected_tool_names = state.get("selected_tools") or []
        current_llm = current_base_llm
        if selected_tool_names and tool_registry:
            tool_objects = tool_registry.get_langchain_tools(selected_tool_names)
            if tool_objects:
                # ── Intent-based tool_choice（前沿方案：Anthropic 推荐）──
                intent = state.get("intent") or {}
                intent_tool_names = intent.get("tool_names")
                needs_tools = (
                    (state.get("goal_mode") and state.get("goal_iterations", 0) > 0)
                    or (intent_tool_names and len(intent_tool_names) > 0)
                )

                # ── 降级检测：上一轮工具失败 → 降级为 auto，允许 LLM 自行回答 ──
                if needs_tools:
                    last_messages = state.get("messages", [])
                    tool_failed_last = False
                    for msg in reversed(last_messages[-3:]):
                        content = _content_to_str(getattr(msg, "content", msg.get("content", "") if isinstance(msg, dict) else ""))
                        if any(kw in content.lower() for kw in ["error", "失败", "不可用", "超时", "timeout", "exception"]):
                            tool_failed_last = True
                            break
                        # 遇到非 tool 消息就停止回溯
                        role = getattr(msg, "role", msg.get("role", "") if isinstance(msg, dict) else "")
                        if role != "tool":
                            break

                    if tool_failed_last:
                        # 工具失败 → 降级为 auto，让 LLM 自行决定
                        current_llm = current_base_llm.bind_tools(tool_objects, tool_choice="auto")
                        logger.info("[llm_call] 上轮工具失败，降级为 tool_choice=auto")
                    else:
                        try:
                            current_llm = current_base_llm.bind_tools(tool_objects, tool_choice="required")
                        except (ValueError, NotImplementedError):
                            current_llm = current_base_llm.bind_tools(tool_objects)
                            logger.warning("[llm_call] tool_choice=required 不支持，降级为 auto")
                else:
                    current_llm = current_base_llm.bind_tools(tool_objects)

                logger.debug(f"[llm_call] 动态绑定 {len(tool_objects)} 个工具 (model={model_label})")
        # selected_tools=[] → 不绑定任何工具（纯对话模式）

        try:
            response = await current_llm.ainvoke(lc_messages)
        except Exception as e:
            logger.error(f"[llm_call] LLM 调用失败: {e}")
            return {
                "messages": [AIMessage(content=f"抱歉，AI 服务暂时不可用：{e}")],
                "final_answer": f"抱歉，AI 服务暂时不可用：{e}",
                "tool_calls": [],
                "error": str(e),
                "is_compacted": _compacted,
            }

        elapsed = time.time() - t0
        has_tools = bool(response.tool_calls)

        # ── 无工具调用时重试（前沿方案：No-tool-call detector）──
        # 意图明确需要工具 或 Goal 模式执行阶段 → 重试
        # 但如果已因工具失败降级为 auto → 不重试，允许 LLM 自行回答
        intent = state.get("intent") or {}
        intent_needs_tools = bool(intent.get("tool_names"))
        # 检查是否已降级（上轮工具失败）
        _last_msgs = state.get("messages", [])
        _tool_degraded = False
        for _msg in reversed(_last_msgs[-3:]):
            _c = _content_to_str(getattr(_msg, "content", _msg.get("content", "") if isinstance(_msg, dict) else ""))
            if any(kw in _c.lower() for kw in ["error", "失败", "不可用", "超时", "timeout", "exception"]):
                _tool_degraded = True
                break
            _r = getattr(_msg, "role", _msg.get("role", "") if isinstance(_msg, dict) else "")
            if _r != "tool":
                break

        if not has_tools and not _tool_degraded and (intent_needs_tools or (state.get("goal_mode") and state.get("goal_iterations", 0) > 0)):
            if selected_tool_names and tool_registry:
                logger.warning("[llm_call] 应调用工具但未调用，强制重试")
                writer({"step": "llm", "status": "retrying", "message": "未调用工具，强制重试..."})
                try:
                    tool_objects = tool_registry.get_langchain_tools(selected_tool_names)
                    try:
                        forced_llm = current_base_llm.bind_tools(tool_objects, tool_choice="required")
                    except (ValueError, NotImplementedError):
                        forced_llm = current_base_llm.bind_tools(tool_objects)
                        logger.warning("[llm_call] 强制重试 tool_choice=required 不支持，降级")
                    response = await forced_llm.ainvoke(lc_messages)
                    has_tools = bool(response.tool_calls)
                    elapsed = time.time() - t0
                    logger.info(f"[llm_call] 强制重试: tool_calls={has_tools}")
                except Exception as retry_e:
                    logger.warning(f"[llm_call] 强制重试失败: {retry_e}")

        logger.info(f"[llm_call] tool_calls={has_tools} elapsed={elapsed:.2f}s iterations={state.get('iterations', 0)}")

        # ── 成本追踪 ──────────────────────────────────
        try:
            usage = getattr(response, "usage_metadata", None) or getattr(response, "usage", None)
            if usage:
                prompt_tokens = getattr(usage, "input_tokens", 0) or (usage.get("input_tokens", 0) if isinstance(usage, dict) else 0)
                completion_tokens = getattr(usage, "output_tokens", 0) or (usage.get("output_tokens", 0) if isinstance(usage, dict) else 0)
                if prompt_tokens or completion_tokens:
                    from app.services.cost_tracker import cost_tracker
                    from app.core.database import AsyncSessionLocal
                    async with AsyncSessionLocal() as cost_db:
                        await cost_tracker.record(
                            db=cost_db,
                            user_id=state.get("user_id", 0),
                            conversation_id=state.get("conversation_id", 0),
                            model_name=getattr(current_base_llm, "model_name", "") or getattr(current_base_llm, "model", ""),
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            duration_ms=int(elapsed * 1000),
                            call_type="chat",
                        )
        except Exception as e:
            logger.debug(f"[llm_call] 成本追踪失败（不影响主流程）: {e}")

        # ── Goal 模式：累加 token 使用量 ──
        goal_tokens_delta = 0
        try:
            usage = getattr(response, "usage_metadata", None) or getattr(response, "usage", None)
            if usage:
                _pt = getattr(usage, "input_tokens", 0) or (usage.get("input_tokens", 0) if isinstance(usage, dict) else 0)
                _ct = getattr(usage, "output_tokens", 0) or (usage.get("output_tokens", 0) if isinstance(usage, dict) else 0)
                goal_tokens_delta = _pt + _ct
        except Exception:
            pass

        result_update = {}
        if goal_tokens_delta and state.get("goal_mode"):
            result_update["goal_tokens_used"] = state.get("goal_tokens_used", 0) + goal_tokens_delta

        # ── Goal 模式：从 LLM 回复中解析 [目标拆解] 并更新 goal_subtasks ──
        if state.get("goal_mode") and response.content:
            answer_text = _content_to_str(response.content)
            parsed = _parse_goal_subtasks(answer_text)
            if parsed:
                result_update["goal_subtasks"] = parsed
                logger.info(f"[llm_call] Goal 模式解析到 {len(parsed)} 个子任务")
                writer({"step": "goal_subtasks", "status": "done", "message": f"任务拆解完成: {len(parsed)} 个子任务", "subtasks": parsed})

        if response.tool_calls:
            tool_names = [tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "") for tc in response.tool_calls]
            writer({"step": "llm", "status": "done", "message": f"需要调用工具: {', '.join(tool_names)} ({elapsed:.1f}s)", "elapsed_ms": int(elapsed * 1000), "has_tools": True})
            return {
                "messages": [AIMessage(content=response.content or "", tool_calls=response.tool_calls)],
                "tool_calls": response.tool_calls,
                "final_answer": None,
                "is_compacted": _compacted,
                **result_update,
            }
        writer({"step": "llm", "status": "done", "message": f"回答生成完成 ({elapsed:.1f}s)", "elapsed_ms": int(elapsed * 1000), "has_tools": False})
        return {
            "messages": [AIMessage(content=response.content)],
            "final_answer": _content_to_str(response.content),
            "tool_calls": [],
            "is_compacted": _compacted,
            **result_update,
        }

    return llm_call_node


def _make_tool_executor(tool_registry):
    """工具执行节点（v5.0 — LangGraph ToolNode 规范化）

    v5.0 重构:
      - 并行执行: 使用 LangGraph 内置并行机制（ToolNode 底层 asyncio.gather）
      - 风险分级: 保留自研（ToolNode 无此能力）
      - 熔断器: 保留自研（ToolNode 无此能力）
      - 重试: 保留自研 2 次重试（ToolNode retry_policy 需要额外配置）
    """
    from langgraph.prebuilt import ToolNode
    from langchain_core.tools import StructuredTool

    async def tool_executor_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        from app.agent.tool_registry import RiskLevel
        writer = get_stream_writer()

        snapshot = tool_registry.create_snapshot()
        tool_calls = state.get("tool_calls", [])

        # ── 1. 分离：需要审批的 vs 可直接执行的 ──────────
        needs_approval = False
        pending_tool = None
        approval_results = []
        executable_calls = []

        for tc in tool_calls:
            tool_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
            tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            tool_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")

            risk = snapshot.get_risk_level(tool_name)
            if risk == RiskLevel.HIGH.value:
                needs_approval = True
                pending_tool = {"id": tool_id, "name": tool_name, "args": tool_args}
                approval_results.append({
                    "role": "tool", "tool_call_id": tool_id,
                    "content": json.dumps({"needs_approval": True, "tool": tool_name,
                        "message": f"⚠️ {tool_name} 是高风险操作，需要用户确认"}, ensure_ascii=False),
                })
                continue

            # 熔断器检查
            if not _circuit_breaker.is_available(tool_name):
                approval_results.append({
                    "role": "tool", "tool_call_id": tool_id,
                    "content": json.dumps(ErrorContract.retryable(tool_name, "工具暂时不可用（熔断中）", attempt=0), ensure_ascii=False),
                })
                continue

            executable_calls.append((tc, tool_name, tool_args, tool_id))

        # ── 2. 使用 LangGraph ToolNode 并行执行 ──────────
        results = list(approval_results)
        tools_succeeded = []

        if executable_calls:
            exec_names = [name for _, name, _, _ in executable_calls]
            writer({"step": "tools", "status": "executing", "message": f"正在执行 {len(exec_names)} 个工具: {', '.join(exec_names)}", "tools": exec_names})
            # 构建 LangChain Tool 列表（ToolNode 需要）
            lc_tools = snapshot.get_langchain_tools(
                [name for _, name, _, _ in executable_calls]
            )
            tool_map = {t.name: t for t in lc_tools}

            # 构建 ToolNode 并执行（ToolNode 内部并行 asyncio.gather）
            tool_node = ToolNode(lc_tools)

            # 构造 AIMessage with tool_calls（ToolNode 输入格式）
            from langchain_core.messages import AIMessage
            ai_msg = AIMessage(content="", tool_calls=[
                {"name": name, "args": args, "id": tid}
                for _, name, args, tid in executable_calls
            ])

            try:
                tool_results = await tool_node.ainvoke({"messages": [ai_msg]})

                for msg in tool_results.get("messages", []):
                    tool_name = getattr(msg, "name", "") or ""
                    tool_call_id = getattr(msg, "tool_call_id", "")
                    content = _content_to_str(msg.content)
                    has_error = "error" in content.lower() or "失败" in content

                    # 熔断器记录
                    if has_error:
                        _circuit_breaker.record_failure(tool_name)
                    else:
                        _circuit_breaker.record_success(tool_name)

                    tools_succeeded.append(tool_name)

                    # tracing 告警
                    try:
                        from app.agent.tracing import check_tool_alert
                        check_tool_alert(tool_name, not has_error)
                    except Exception:
                        pass

                    results.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": content,
                    })

            except Exception as e:
                logger.error(f"[tool_executor] ToolNode 执行异常，降级为逐个执行: {e}")
                # 降级为逐个执行（每个工具独立 try/except）
                for _, name, args, tid in executable_calls:
                    try:
                        result = await snapshot.execute(name, args)
                        has_err = isinstance(result, dict) and result.get("error") is not None
                        if has_err:
                            _circuit_breaker.record_failure(name)
                        else:
                            _circuit_breaker.record_success(name)
                        tools_succeeded.append(name)
                        try:
                            from app.agent.tracing import check_tool_alert
                            check_tool_alert(name, not has_err)
                        except Exception:
                            pass
                        results.append({
                            "role": "tool", "tool_call_id": tid, "name": name,
                            "content": _format_tool_result_json(result, name),
                        })
                    except Exception as tool_err:
                        _circuit_breaker.record_failure(name)
                        results.append({
                            "role": "tool", "tool_call_id": tid, "name": name,
                            "content": _format_tool_result_json(None, name, str(tool_err)),
                        })

        # 工具执行完成（无论成功失败都发 done 事件）
        all_names = [name for _, name, _, _ in executable_calls]
        failed_names = [n for n in all_names if n not in tools_succeeded]
        if failed_names:
            writer({"step": "tools", "status": "error", "message": f"工具执行完成: {', '.join(tools_succeeded)} 成功, {', '.join(failed_names)} 失败", "succeeded": tools_succeeded, "failed": failed_names})
        else:
            writer({"step": "tools", "status": "done", "message": f"工具执行完成: {', '.join(tools_succeeded)}", "succeeded": tools_succeeded})

        return {
            "messages": results,
            "tools_used": tools_succeeded,
            "current_tools_used": tools_succeeded,
            "tool_calls": [],
            "iterations": state.get("iterations", 0) + 1,
            "needs_approval": needs_approval,
            "pending_tool_call": pending_tool,
        }

    return tool_executor_node


def _make_approval_node(tool_registry):
    """审批节点 — interrupt/resume 正式实现

    流程:
      1. Agent 执行到此节点 → interrupt() 暂停，返回待审批信息给前端
      2. 前端展示给用户确认/拒绝
      3. 前端调用 resume API → Command(resume={"approved": True/False})
      4. Agent 从暂停处继续执行
    """

    async def approval_node(state: AgentState) -> dict:
        pending = state.get("pending_tool_call")
        if not pending:
            return {"needs_approval": False, "pending_tool_call": None}

        # interrupt/resume 模式（需要 checkpointer）
        decision = interrupt({
            "type": "approval_required",
            "tool": pending["name"],
            "args": pending["args"],
            "message": f"工具 {pending['name']} 需要您的确认才能执行",
        })

        if isinstance(decision, dict) and decision.get("approved"):
            result = await tool_registry.execute(pending["name"], pending["args"], approved=True)
            return {
                "messages": [{"role": "tool", "tool_call_id": pending["id"],
                    "content": _format_tool_result_json(result, pending["name"])}],
                "tools_used": [pending["name"]],
                "needs_approval": False,
                "pending_tool_call": None,
            }
        else:
            return {
                "messages": [{"role": "tool", "tool_call_id": pending["id"],
                    "content": "用户拒绝执行此操作"}],
                "needs_approval": False,
                "pending_tool_call": None,
            }

    return approval_node


def _make_evaluator_node(llm=None):
    """评估节点 — LLM-as-Judge（替代纯规则评估）

    评估维度:
      1. 准确性 — 回答是否正确
      2. 完整性 — 是否回答了用户的问题
      3. 幻觉检测 — 是否包含捏造信息
      4. 工具使用 — 工具调用结果是否被正确引用

    当 llm 不可用时降级为规则评估。
    """

    # 规则评估降级版（仅在无 LLM 时使用）
    def _rule_based_eval(state) -> dict:
        final_answer = state.get("final_answer", "")
        if not final_answer:
            return {"evaluation": {"passed": False, "reason": "无回答", "score": 0}}
        if len(final_answer.strip()) < 10:
            return {"evaluation": {"passed": False, "reason": "回答过短", "score": 2},
                    "final_answer": "抱歉，我暂时无法准确回答这个问题。你可以换个方式描述，或稍后再试。"}
        if "抱歉" in final_answer and "不可用" in final_answer:
            return {"evaluation": {"passed": False, "reason": "包含错误信息", "score": 2}}
        return {"evaluation": {"passed": True, "reason": "", "score": 7}}

    async def evaluator_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        # Goal 模式: 执行评估但不替换 final_answer（反馈给 status_updater 使用）
        if state.get("goal_mode"):
            # 仍然执行评估以产生质量反馈
            if not llm or not final_answer:
                writer({"step": "eval", "status": "skipped", "message": "Goal 模式，无 LLM 或无回答，跳过评估"})
                return {"evaluation": {"passed": True, "reason": "goal_mode_skip", "score": 8}}

            writer({"step": "eval", "status": "checking", "message": "Goal 模式质量检查..."})
            # 复用 LLM-as-Judge 评估
            user_query = _extract_last_message(state)
            eval_prompt = f"""评估以下子任务执行质量。

【子任务】
{user_query}

【执行结果】
{final_answer[:1500]}

评分标准：
- score >= 6: 通过，执行结果有效
- score < 6: 未通过，需要重试

严格按 JSON 输出：
{{"score": 8, "passed": true, "reason": "简短说明", "suggestion": "改进建议（如果未通过）"}}
"""
            try:
                from app.agent.structured_schemas import EvaluationResult
                structured_llm = llm.with_structured_output(EvaluationResult)
                result = await structured_llm.ainvoke([HumanMessage(content=eval_prompt)])
                if result:
                    evaluation = {"score": result.score, "passed": result.passed, "reason": result.reason}
                    writer({"step": "eval", "status": "done",
                            "message": f"Goal 质量检查: {result.score}/10 {'通过' if result.passed else '未通过'}"})
                    # 注意：不替换 final_answer，让 status_updater 处理
                    return {"evaluation": evaluation}
            except Exception as e:
                logger.debug(f"[evaluator] Goal 模式评估失败: {e}")

            return {"evaluation": {"passed": True, "reason": "goal_mode_skip", "score": 8}}

        final_answer = state.get("final_answer", "")
        if not final_answer:
            writer({"step": "eval", "status": "skipped", "message": "无回答，跳过评估"})
            return {"evaluation": {"passed": False, "reason": "无回答", "score": 0}}

        writer({"step": "eval", "status": "checking", "message": "正在评估回答质量..."})

        # 无 LLM 时降级为规则评估
        if not llm:
            return _rule_based_eval(state)

        # LLM-as-Judge
        user_query = _extract_last_message(state)
        tools_used = state.get("tools_used", [])
        memory_ctx = state.get("memory_context") or {}

        # 记忆质量上下文
        memory_info = ""
        if memory_ctx.get("count", 0) > 0:
            avg_score = memory_ctx.get("avg_score", 0)
            memory_info = f"\n【检索到的记忆】{memory_ctx['count']}条，平均相关度: {avg_score:.2f}"

        eval_prompt = f"""你是一个严格的质量评估专家。请评估以下 AI 回答的质量。

【用户问题】
{user_query}

【AI 回答】
{final_answer[:2000]}

【使用的工具】
{', '.join(tools_used) if tools_used else '无'}{memory_info}

请从以下维度评估（1-10分）:
1. 准确性 — 回答是否正确、是否有事实错误
2. 完整性 — 是否完整回答了用户的问题
3. 幻觉检测 — 是否包含捏造的信息或数据
4. 工具使用 — 如果使用了工具，结果是否被正确引用
5. 记忆引用 — 如果检索到了记忆，回答中是否正确引用了记忆内容（无记忆时给 7 分）

严格按以下 JSON 格式返回（不要输出其他内容）:
{{"score": 8, "passed": true, "reason": "简短说明", "dimensions": {{"accuracy": 8, "completeness": 7, "hallucination": 9, "tool_usage": 8, "memory_usage": 7}}}}

注意:
- score >= 6 为通过
- 如果回答包含明显的错误信息或"服务不可用"等，score <= 3
- 如果使用了工具但回答中没有引用工具结果，tool_usage <= 4
- 如果检索到了相关记忆但回答完全没体现，memory_usage <= 4"""

        try:
            from app.agent.structured_schemas import EvaluationResult
            from langchain_core.messages import HumanMessage, SystemMessage

            structured_llm = llm.with_structured_output(EvaluationResult)
            result = await structured_llm.ainvoke([
                SystemMessage(content="你是一个严格的质量评估专家。"),
                HumanMessage(content=eval_prompt),
            ])

            if result is None:
                logger.warning("[evaluator] LLM 返回 None，降级为规则评估")
                return _rule_based_eval(state)

            evaluation = {
                "score": result.score,
                "passed": result.passed,
                "reason": result.reason,
                "dimensions": {
                    "accuracy": result.dimensions.accuracy,
                    "completeness": result.dimensions.completeness,
                    "hallucination": result.dimensions.hallucination,
                    "tool_usage": result.dimensions.tool_usage,
                    "memory_usage": result.dimensions.memory_usage,
                },
            }
            logger.info(f"[evaluator] LLM-as-Judge: score={evaluation['score']} passed={evaluation['passed']} reason={evaluation['reason'][:50]}")

            score = evaluation['score']
            passed = evaluation['passed']
            if passed:
                writer({"step": "eval", "status": "done", "message": f"质量评估通过 (评分 {score}/10)", "score": score})
            else:
                reason = evaluation.get('reason', '')
                writer({"step": "eval", "status": "done", "message": f"质量评估未通过 (评分 {score}/10, {reason})", "score": score})

            # 评分太低（<4）的回答替换为兜底
            eval_result = {"evaluation": evaluation}
            if evaluation["score"] < 4 and state.get("final_answer"):
                logger.warning(f"[evaluator] 评估不通过(score={evaluation['score']})，替换为兜底回答")
                eval_result["final_answer"] = (
                    "抱歉，我暂时无法准确回答这个问题。"
                    "可能是搜索服务暂时不可用，或者问题超出了我当前的能力范围。\n\n"
                    "你可以试试：\n"
                    "1. 换个方式描述你的问题\n"
                    "2. 稍后再试\n"
                    "3. 如果是天气等实时信息，可以直接告诉我你的城市"
                )
            return eval_result

        except Exception as e:
            logger.warning(f"[evaluator] LLM 评估失败，降级为规则评估: {e}")
            return _rule_based_eval(state)

    return evaluator_node


def _make_memory_saver(memory_manager):
    async def memory_saver_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        # Goal 模式: 跳过中间轮次的记忆保存
        if state.get("goal_mode") and state.get("goal_status") not in ("achieved", "failed", "budget_exceeded"):
            return {}

        if not state.get("final_answer"):
            return {}

        writer({"step": "memory_save", "status": "saving", "message": "正在保存记忆..."})

        messages = _build_message_dicts(state)
        importance = state.get("conversation_importance")

        # 短期记忆: Redis
        if memory_manager:
            try:
                await memory_manager.update_session_cache(
                    conversation_id=state["conversation_id"],
                    messages=messages + [{"role": "assistant", "content": state["final_answer"]}],
                )
            except Exception as e:
                logger.warning(f"[memory_saver] Redis 保存失败: {e}")

            # ── 长期记忆: 基于 conversation_importance 的智能保存 ──
            # 计算对话重要性（如果 State 已有则复用）
            if importance is None:
                importance = memory_manager._score_conversation_importance(
                    messages + [{"role": "assistant", "content": state["final_answer"]}]
                )

            tools_used = state.get("tools_used", [])

            # 保存条件（三选一）:
            #   1. 有工具调用 → 实际执行了任务，值得记录
            #   2. 对话轮次 >= 8 且重要性 >= 6 → 深度且有价值的对话
            #   3. 重要性 >= 8 → 高价值对话（不管有没有工具）
            should_save = (
                tools_used
                or (len(messages) >= 8 and importance >= 6)
                or importance >= 8
            )

            if should_save:
                try:
                    enqueued = await memory_manager.enqueue_summary(
                        conversation_id=state["conversation_id"],
                        user_id=state.get("user_id", 0),
                        messages=messages + [{"role": "assistant", "content": state["final_answer"]}],
                    )
                    if enqueued:
                        logger.info(f"[memory_saver] 长期记忆已入队(异步): importance={importance} tools={bool(tools_used)} msgs={len(messages)}")
                    else:
                        logger.debug(f"[memory_saver] 跳过保存: importance={importance} tools={bool(tools_used)} msgs={len(messages)}")
                except Exception as e:
                    logger.warning(f"[memory_saver] 摘要入队失败: {e}")
            else:
                logger.debug(f"[memory_saver] 跳过保存: importance={importance} tools={bool(tools_used)} msgs={len(messages)}")

            # ── Markdown 每日日志：每次对话都追加 ──
            try:
                from app.core.database import AsyncSessionLocal
                from app.services.markdown_memory_service import markdown_memory_service
                from datetime import datetime

                user_content = ""
                for m in messages:
                    if m.get("role") == "user":
                        user_content = _content_to_str(m.get("content", ""))
                        break

                assistant_answer = state.get("final_answer", "")
                # enqueue_summary 异步模式下无 meta，用用户首条消息作为摘要
                summary_text = (user_content[:100] + "...") if len(user_content) > 100 else user_content

                now = datetime.utcnow()
                time_str = now.strftime("%H:%M")
                conv_id = state["conversation_id"]

                # 生成会话标题（首次对话时自动设置）
                conv_title = state.get("conversation_title", "")
                if not conv_title and user_content:
                    conv_title = user_content[:20].replace("\n", " ").strip()
                    if len(user_content) > 20:
                        conv_title += "..."

                log_entry = f"## {time_str} | {conv_title}\n{summary_text}\n"

                async with AsyncSessionLocal() as md_db:
                    await markdown_memory_service.append_daily_log(
                        md_db, user_id=state.get("user_id", 0), content=log_entry,
                    )
                    await md_db.commit()
                    logger.info(f"[memory_saver] Markdown daily log 已追加: {conv_title}")

                    # ── 自动生成会话标题（首条消息）──
                    if not state.get("conversation_title") and user_content:
                        try:
                            from app.repository.conversation_repo import ConversationRepository
                            conv_repo = ConversationRepository()
                            conv = await conv_repo.find_by_id(md_db, conv_id)
                            if conv and (not conv.title or conv.title == "新会话"):
                                pass  # 标题已移到 ChatService.save_skill_messages 统一处理
                        except Exception as e:
                            logger.warning(f"[memory_saver] 会话标题更新失败: {e}")

            except Exception as e:
                logger.warning(f"[memory_saver] Markdown daily log 失败: {e}")

        # ── P0: 跨线程长期记忆（MySQL CrossThreadMemory）──
        if state.get("final_answer"):
            try:
                import uuid
                from app.core.database import AsyncSessionLocal
                from app.repository.cross_thread_memory_repo import CrossThreadMemoryRepository
                user_query = ""
                for m in messages:
                    if m.get("role") == "user":
                        user_query = _content_to_str(m.get("content", ""))[:200]
                        break
                memory_entry = {
                    "query": user_query,
                    "answer": (state.get("final_answer") or "")[:500],
                    "tools": state.get("tools_used", []),
                    "importance": importance or 0,
                    "conversation_id": state.get("conversation_id", 0),
                }
                async with AsyncSessionLocal() as mem_db:
                    repo = CrossThreadMemoryRepository()
                    await repo.create(mem_db, {
                        "user_id": state.get("user_id", 0),
                        "namespace": "conversations",
                        "memory_key": str(uuid.uuid4()),
                        "content": memory_entry,
                    })
                    await mem_db.commit()
                    logger.info(f"[memory_saver] 跨线程记忆已保存: user_id={state.get('user_id', 0)}")
            except Exception as e:
                logger.debug(f"[memory_saver] 跨线程记忆保存跳过: {e}")

        writer({"step": "memory_save", "status": "done", "message": "记忆保存完成"})
        return {"conversation_importance": importance}

    return memory_saver_node




def _route_after_intent(state: AgentState) -> str:
    intent = state.get("intent")
    if intent and intent.get("cached_answer") and state.get("final_answer"):
        return "cache_return"
    if intent and intent.get("target_module") and intent["target_module"] != "cache":
        return "skill"
    return "agent"


def _should_use_tools(state: AgentState) -> str:
    if state.get("iterations", 0) >= 10:
        logger.warning("[agent] 工具调用达到上限(10轮)，强制结束")
        return "finish"
    if state.get("needs_approval"):
        return "finish"
    if state.get("skill_answer"):
        return "finish"
    if state.get("tool_calls"):
        return "use_tools"
    return "finish"


def _after_tool_exec(state: AgentState) -> str:
    if state.get("needs_approval"):
        return "needs_approval"
    return "continue"


def _after_approval(state: AgentState) -> str:
    if state.get("needs_approval"):
        return "rejected"
    return "approved"


def _after_eval(state: AgentState) -> str:
    evaluation = state.get("evaluation", {})
    passed = evaluation.get("passed", True)
    score = evaluation.get("score", 7)

    # score >= 6 或 passed=True → 通过
    if passed and score >= 6:
        return "pass"

    # 评估未通过但已有回答 → 仍然放行（兜底回答已在 evaluator 节点中替换）
    if state.get("final_answer"):
        return "pass"
    return "replan"


def _after_memory(state: AgentState) -> str:
    """memory_saver 之后的路由 — Goal 模式走状态更新器，终态则结束"""
    if state.get("goal_mode"):
        # 终态（achieved/failed/budget_exceeded）→ 结束，不再循环
        if state.get("goal_status") in ("achieved", "failed", "budget_exceeded"):
            return END
        return "goal_status_updater"
    return END


def _after_goal_eval(state: AgentState) -> str:
    """goal_evaluator 之后的路由 — 达成/超限→结束，未达成→重试"""
    status = state.get("goal_status", "")
    if status in ("achieved", "budget_exceeded", "failed"):
        return END
    return "model_selector"


def _after_goal_replan(state: AgentState) -> str:
    """goal_replanner 之后的路由 — 达成直接保存记忆，不再重复评估"""
    status = state.get("goal_status", "")
    if status == "achieved":
        return "memory_saver"
    if status in ("budget_exceeded", "failed"):
        return END
    return "model_selector"


# ── 辅助函数 ──────────────────────────────────────────────

def _select_tool_names_for_intent(state, tool_registry) -> list:
    """
    B+C 核心：根据 intent 动态选择工具名。

    Returns:
        工具名字符串列表（可序列化，存入 state 供 llm_call 使用）
    """
    if not tool_registry:
        return []

    intent = state.get("intent")
    if not intent:
        # 无 intent → 全量（Agent 兜底模式）
        return [t.name for t in tool_registry.list_tools()]

    tool_names = intent.get("tool_names")
    if tool_names is None:
        # null → 全量（Agent 模式）
        return [t.name for t in tool_registry.list_tools()]

    if not tool_names:
        # [] → 纯对话，不需要工具
        return []

    # 指定工具列表 → 过滤（只保留 registry 中存在的）
    all_names = {t.name for t in tool_registry.list_tools()}
    return [n for n in tool_names if n in all_names]

def _extract_last_message(state) -> str:
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    if last_msg:
        content = last_msg.get("content", "") if isinstance(last_msg, dict) else getattr(last_msg, "content", "")
        return _content_to_str(content)
    return ""


