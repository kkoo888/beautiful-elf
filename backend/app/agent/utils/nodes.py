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
    ErrorContract, CircuitBreaker, _circuit_breaker, MAX_MESSAGE_WINDOW, get_max_message_window,
    _content_to_str, _build_message_dicts,
    _trim_messages, _format_tool_result_json,
)
from app.agent.message_sanitizer import sanitize_messages, repair_tool_arguments
from app.agent.tool_dispatch import should_parallelize_tool_batch, wrap_untrusted_result
from app.agent.error_classifier import classify_error, FailoverReason
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
            "tier_config": model_selector.get_tier_config(decision.tier),
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
        if intent:
            logger.info(f"[intent_router] intent_detail: name={intent.get('intent_name')} score={intent.get('score', 0):.3f} tool_names={intent.get('tool_names')} target_module={intent.get('target_module')}")

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
                _max_chars = getattr(context_engine, '_max_context_chars', MAX_CONTEXT_CHARS)
                if result.total_chars > _max_chars:
                    system_prompt = await context_engine.compress_context(
                        system_prompt, target_chars=_max_chars
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
                system_prompt = "你是主人知识最全面的军师，能够使用工具回答用户问题。请用中文回答。"
        else:
            system_prompt = "你是主人知识最全面的军师，能够使用工具回答用户问题。请用中文回答。"
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

        # ── 路由闭环：prompt_policy 控制 prompt 复杂度 ──
        # frontend 传入 auto/concise/balanced/detailed，auto 时由 ML 路由决定
        prompt_policy = state.get("prompt_policy", "auto")
        tier = state.get("tier", "")

        if prompt_policy == "auto":
            # ML 路由: S/M → concise; L/XL → balanced
            effective_policy = "concise" if tier in ("S", "M") else "balanced"
        else:
            effective_policy = prompt_policy

        if effective_policy == "concise":
            # 精简模式：去掉 RAG、主动回忆、跨线程记忆，只保留 soul + 核心指令
            # 重新组装：取 system_prompt 的前半部分（soul + 核心行为准则）
            _soul_end = system_prompt.find("## 工具使用规则")
            if _soul_end > 0:
                system_prompt = system_prompt[:_soul_end].rstrip()
            logger.info(f"[context_builder] prompt_policy=concise, 已精简 system_prompt")
        elif effective_policy == "detailed":
            # 详细模式：确保所有上下文都注入（当前已是默认行为，无需额外处理）
            logger.info(f"[context_builder] prompt_policy=detailed, 保持完整上下文")
        # balanced: 当前行为，无需修改

        return {
            "system_prompt": system_prompt,
            "context": system_prompt,
            "memory_context": memory_context,
            "selected_tools": selected_tool_names,
        }

    return context_builder_node


def _make_llm_caller(llm, tool_registry=None, model_selector=None, context_length: int = 0):
    async def llm_call_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        t0 = time.time()

        # ── 按路由结果动态选择 LLM ──
        selected_model = state.get("selected_model") or ""
        if model_selector and selected_model:
            # 获取 fallback 模型名（从 tier_config 中读取）
            tier_cfg = state.get("tier_config") or {}
            fallback_model = tier_cfg.get("fallback_model_name", "")
            current_base_llm = model_selector.get_llm(selected_model, fallback_model=fallback_model)
            model_label = selected_model
        else:
            current_base_llm = llm
            model_label = state.get("model_name") or "default"

        # ── 请求级 temperature/max_tokens 覆盖（前端传入时生效）──
        req_temp = state.get("temperature", 0)
        req_max_tokens = state.get("max_tokens", 0)
        if req_temp > 0 or req_max_tokens > 0:
            try:
                from app.llm.langchain_adapter import ChatLLMProvider
                cur_temp = getattr(current_base_llm, 'temperature', 0.7)
                cur_max = getattr(current_base_llm, 'max_tokens', 4096)
                new_temp = req_temp if req_temp > 0 else cur_temp
                new_max = req_max_tokens if req_max_tokens > 0 else cur_max
                if new_temp != cur_temp or new_max != cur_max:
                    new_llm = ChatLLMProvider(
                        provider=current_base_llm.provider,
                        temperature=new_temp,
                        max_tokens=new_max,
                    )
                    # 继承原 LLM 的工具绑定（ChatLLMProvider 是 Pydantic，用 model_copy）
                    if hasattr(current_base_llm, '_bound_tools') and current_base_llm._bound_tools:
                        new_llm._bound_tools = list(current_base_llm._bound_tools)
                        new_llm._bound_tool_choice = getattr(current_base_llm, '_bound_tool_choice', None)
                    current_base_llm = new_llm
                    logger.info(f"[llm_call] 请求级覆盖: temp={new_temp}, max_tokens={new_max}")
            except Exception as e:
                logger.debug(f"[llm_call] 请求级参数覆盖跳过: {e}")

        # 路由信息
        thinking_mode = state.get("thinking_mode", "")
        prompt_policy = state.get("prompt_policy", "")
        prompt_hint = state.get("prompt_hint", "")
        route_class = state.get("route_class", "")
        tier = state.get("tier", "")

        # ── 路由闭环：reasoning_depth 决策 ──
        # frontend 传入 auto/fast/deep/full，auto 时由 ML 路由 thinking_mode 决定
        reasoning_depth = state.get("reasoning_depth", "auto")
        if reasoning_depth == "auto":
            # ML 路由: T0/T1 → 禁用 reasoning; T2/T3 → 启用
            effective_reasoning = thinking_mode in ("T2", "T3")
        elif reasoning_depth == "fast":
            effective_reasoning = False
        elif reasoning_depth in ("deep", "full"):
            effective_reasoning = True
        else:
            effective_reasoning = thinking_mode in ("T2", "T3")

        # ── 路由闭环：tier 决定 temperature/max_tokens ──
        tier_overrides = {
            "S":  {"temperature": 0.3, "max_tokens": 1024},
            "M":  {"temperature": 0.5, "max_tokens": 2048},
            "L":  {"temperature": 0.7, "max_tokens": 8192},
            "XL": {"temperature": 0.7, "max_tokens": 16384},
        }
        # 仅当 frontend 未显式指定时，才用 tier 覆盖
        if tier and tier in tier_overrides and req_temp == 0 and req_max_tokens == 0:
            tier_cfg = tier_overrides[tier]
            try:
                from app.llm.langchain_adapter import ChatLLMProvider
                new_llm = ChatLLMProvider(
                    provider=current_base_llm.provider,
                    temperature=tier_cfg["temperature"],
                    max_tokens=tier_cfg["max_tokens"],
                )
                if hasattr(current_base_llm, '_bound_tools') and current_base_llm._bound_tools:
                    new_llm._bound_tools = list(current_base_llm._bound_tools)
                    new_llm._bound_tool_choice = getattr(current_base_llm, '_bound_tool_choice', None)
                current_base_llm = new_llm
                logger.info(f"[llm_call] tier 覆盖: tier={tier} temp={tier_cfg['temperature']} max_tokens={tier_cfg['max_tokens']}")
            except Exception as e:
                logger.debug(f"[llm_call] tier 覆盖跳过: {e}")

        writer({"step": "llm", "status": "calling", "message": f"正在生成回答... (模型: {model_label}, 路由: {route_class}/{tier}, 思考: {thinking_mode}, reasoning: {effective_reasoning})"})

        system_prompt = state.get("system_prompt") or state.get("context") or \
            "你是主人知识最全面的军师，能够使用工具回答用户问题。请用中文回答。"

        # 注入路由提示
        if prompt_hint:
            system_prompt = f"{system_prompt}\n\n【指令】{prompt_hint}"

        # ── Cache Continuity：tier 从高降回低时，注入压缩指令 ──
        _TIER_RANK = {"S": 0, "M": 1, "L": 2, "XL": 3}
        prev_tier = state.get("_prev_tier", "")
        if prev_tier and tier:
            prev_rank = _TIER_RANK.get(prev_tier, 0)
            curr_rank = _TIER_RANK.get(tier, 0)
            if prev_rank > curr_rank:
                # 从高 tier 降回低 tier，注入精简指令
                system_prompt += "\n\n【缓存连续性】上文较长，请简洁回答，避免重复已讨论的内容，控制在 500 字以内。"

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
6. 子任务数量控制在 3-10 个
7. 制定完后就开始执行子任务

## 依赖规则
- 如果任务 B 需要任务 A 的结果才能开始，设置 dependencies: [A的id]
- 无依赖的任务可以并行执行
- id 从 1 开始递增"""
                try:
                    plan_result = await plan_llm.ainvoke([HumanMessage(content=plan_prompt)])
                    if not plan_result or not getattr(plan_result, "subtasks", None):
                        return {"final_answer": "❌ 规划失败：模型未返回有效计划", "is_error": True, "goal_status": "failed"}
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
6. **完成后通知下一个** — 完成后需要通知下一个子任务开始执行

{eval_feedback_text}
{healing_context}"""


            # 注意：iterations == 0 的 prompt 已在上方行 535-571 定义，此处不再重复


        lc_messages = [SystemMessage(content=system_prompt)]

        # ── 消息清理（修复畸形 JSON + Unicode 代理）──
        raw_messages = state["messages"]
        _msg_dicts = [{"role": getattr(m, "role", "user"), "content": _content_to_str(getattr(m, "content", ""))} for m in raw_messages]
        if sanitize_messages(_msg_dicts):
            logger.info("[llm_call] 消息清理: 修复了 Unicode 代理对")

        # ── Auto-Compaction（压缩旧历史，仅首次检查）──────
        _window = get_max_message_window()
        if len(raw_messages) > _window and not state.get("is_compacted"):
            try:
                from app.agent.compaction import maybe_compact
                raw_messages = await maybe_compact(
                    messages=[{"role": getattr(m, "role", "user"), "content": _content_to_str(getattr(m, "content", ""))} for m in raw_messages],
                    llm_client=llm,
                    user_id=state.get("user_id", 0),
                    conversation_id=state.get("conversation_id", 0),
                    max_tokens=context_length,  # context_length = 模型上下文窗口大小，传给 compactor 作为压缩阈值
                )
                _compacted = True
            except Exception as e:
                logger.warning(f"[llm_call] compaction 失败，降级为窗口裁剪: {e}")
                raw_messages = _trim_messages(raw_messages, _window)
                _compacted = True
        else:
            raw_messages = _trim_messages(raw_messages, _window)
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

        # ── 日志：打印发给 LLM 的完整请求 ──
        _log_msgs = []
        for _m in lc_messages:
            _role = getattr(_m, "role", None) or getattr(_m, "type", "unknown")
            _content = _content_to_str(getattr(_m, "content", ""))
            _tc = getattr(_m, "tool_calls", None)
            _tid = getattr(_m, "tool_call_id", None)
            _entry = {"role": _role, "content": _content[:500]}
            if _tc:
                _entry["tool_calls"] = [{"name": t.get("name", ""), "args": str(t.get("args", {}))[:200]} for t in _tc]
            if _tid:
                _entry["tool_call_id"] = _tid
            _log_msgs.append(_entry)
        _bound_tools = [t.name for t in tool_objects] if tool_objects else []
        _tc_setting = getattr(current_llm, '_bound_tool_choice', None)
        logger.info(f"[llm_call] REQUEST: tools={_bound_tools} tool_choice={_tc_setting} messages={json.dumps(_log_msgs, ensure_ascii=False)}")

        try:
            response = await current_llm.ainvoke(lc_messages)
        except Exception as e:
            # LangGraph 官方模式：错误通过 writer 推送 + 存入 state.error
            # 不污染 messages（对话历史），避免下轮 LLM 上下文被污染
            logger.error(f"[llm_call] LLM 调用失败: {e}")
            writer({"step": "llm", "status": "error", "message": f"LLM 调用失败: {str(e)[:100]}"})
            error_answer = "抱歉，AI 服务暂时不可用，请稍后重试。"
            return {
                "final_answer": error_answer,
                "tool_calls": [],
                "error": str(e),
                "is_error": True,
                "is_compacted": _compacted,
            }

        elapsed = time.time() - t0
        has_tools = bool(response.tool_calls)

        # ── 日志：打印 LLM 返回结果 ──
        _resp_content = _content_to_str(getattr(response, "content", "")) if response.content else ""
        _resp_tool_calls = [{"name": t.get("name", ""), "args": str(t.get("args", {}))[:200]} for t in (response.tool_calls or [])]
        logger.info(f"[llm_call] RESPONSE: elapsed={elapsed:.2f}s has_tools={has_tools} tool_calls={json.dumps(_resp_tool_calls, ensure_ascii=False)} content={_resp_content[:300]}")

        # ── 无工具调用时重试（前沿方案：No-tool-call detector）──
        # 意图明确需要工具 或 Goal 模式执行阶段 或 LLM 嘴上说要搜索但没调工具 → 重试
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

        # LLM 回答涉及搜索/查询但没调工具 → 视为需要重试
        # 但如果回答已经足够完整（> 100字符且不含抱歉），不重试
        _response_text = _content_to_str(getattr(response, "content", "")) if response.content else ""
        _mentions_search = any(kw in _response_text for kw in ["搜索", "查询", "查找", "检索", "搜一下", "帮你找", "帮你查", "让我查", "让我搜"])
        _already_answered = len(_response_text.strip()) > 100 and "抱歉" not in _response_text[:30]

        _needs_retry = (
            intent_needs_tools
            or (state.get("goal_mode") and state.get("goal_iterations", 0) > 0)
            or (_mentions_search and selected_tool_names)
        )

        if not has_tools and not _tool_degraded and not _already_answered and _needs_retry:
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
                    # ── 日志：打印强制重试请求 ──
                    _retry_bound_tools = [t.name for t in tool_objects] if tool_objects else []
                    _retry_tc = getattr(forced_llm, '_bound_tool_choice', None)
                    logger.info(f"[llm_call] RETRY REQUEST: tools={_retry_bound_tools} tool_choice={_retry_tc}")
                    response = await forced_llm.ainvoke(lc_messages)
                    has_tools = bool(response.tool_calls)
                    elapsed = time.time() - t0
                    # ── 日志：打印强制重试结果 ──
                    _retry_resp_content = _content_to_str(getattr(response, "content", "")) if response.content else ""
                    _retry_resp_tc = [{"name": t.get("name", ""), "args": str(t.get("args", {}))[:200]} for t in (response.tool_calls or [])]
                    logger.info(f"[llm_call] RETRY RESPONSE: tool_calls={has_tools} tc={json.dumps(_retry_resp_tc, ensure_ascii=False)} content={_retry_resp_content[:300]}")
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
        # 存储当前 tier 供下一轮 Cache Continuity 使用
        if tier:
            result_update["_prev_tier"] = tier
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


def _make_tool_executor(tool_registry, llm=None):
    """工具执行节点（v5.1 — 工具失败自动 LLM 推理）

    v5.1: 工具失败 → LLM 自主推理替代（不降级）
    v5.0: LangGraph ToolNode 并行 + 风险分级 + 熔断器 + 重试
    """
    from langgraph.prebuilt import ToolNode
    from langchain_core.tools import StructuredTool
    llm_ref = llm  # 供 fallback 使用

    async def tool_executor_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        from app.agent.tool_registry import RiskLevel
        writer = get_stream_writer()

        snapshot = tool_registry.create_snapshot()
        tool_calls = state.get("tool_calls", [])
        goal_task_id = state.get("goal_current_task_id", 0)

        # 如果在 Goal 模式中，通知前端当前工具属于哪个子任务
        if goal_task_id and tool_calls:
            tool_names = [tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "") for tc in tool_calls]
            writer({"step": "goal_tools", "status": "executing",
                    "message": f"子任务 #{goal_task_id} 正在调用工具",
                    "taskId": goal_task_id, "tools": tool_names})

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
                    # 不可信工具结果加标签（防注入）
                    content = wrap_untrusted_result(tool_name, content)
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

        # ── 工具失败 → LLM 自主推理（不降级，直接用大模型查资料）──
        if failed_names and llm_ref:
            llm_fallback_results = []
            for tc, tool_name, tool_args, tool_id in executable_calls:
                if tool_name in failed_names:
                    try:
                        query = tool_args.get("query", "") or tool_args.get("input", "") or tool_args.get("question", "") or str(tool_args)[:200]
                        fallback_prompt = f"""工具 "{tool_name}" 执行失败。请用你自己的知识直接回答以下问题。

问题: {query}

要求:
1. 用你训练数据中的知识直接回答
2. 如果涉及实时信息（天气、股价等），说明这是基于你训练数据的推测
3. 给出尽可能具体和有用的回答
4. 在回答末尾注明: [注意: 此回答来自模型推理，非实时工具查询]"""
                        from langchain_core.messages import HumanMessage
                        resp = await llm_ref.ainvoke([HumanMessage(content=fallback_prompt)])
                        fallback_content = _content_to_str(resp.content)
                        if fallback_content and len(fallback_content.strip()) > 20:
                            # 替换失败结果为 LLM 推理结果
                            for r in results:
                                if isinstance(r, dict) and r.get("tool_call_id") == tool_id:
                                    r["content"] = json.dumps({
                                        "source": "llm_reasoning",
                                        "tool_failed": tool_name,
                                        "result": fallback_content,
                                        "note": "工具失败，此结果来自模型自主推理"
                                    }, ensure_ascii=False)
                                    tools_succeeded.append(fallback_content[:20] + "...")
                                    break
                            llm_fallback_results.append(tool_name)
                            writer({"step": "tools", "status": "llm_fallback",
                                    "message": f"工具 {tool_name} 失败，已用模型推理替代",
                                    "tool": tool_name})
                    except Exception as fb_err:
                        logger.warning(f"[tool_executor] LLM fallback 失败: {fb_err}")
            if llm_fallback_results:
                failed_names = [n for n in failed_names if n not in llm_fallback_results]

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
    """评估节点 — 混合方案（增强规则 + LLM-as-Judge）

    两阶段评估:
      Phase 1 — 增强规则（零 LLM 调用，快速过滤明显差/好的回答）
      Phase 2 — LLM-as-Judge（仅对边界 case 做语义评估，score 5-8）

    当 llm 不可用时降级为纯规则评估。
    """

    # ── Phase 1: 增强规则评估 ──
    def _rule_based_score(final_answer: str, tools_used: list, memory_ctx: dict) -> tuple[int, list[str]]:
        """返回 (score, reasons)，score 范围 1-10。"""
        score = 4  # 基础分降低，避免垃圾回答轻易过关
        reasons = []

        # 规则 1: 回答长度
        ans_len = len(final_answer.strip())
        if ans_len < 10:
            score = 1
            reasons.append("回答过短")
        elif ans_len < 50:
            score -= 2
            reasons.append("回答较短")
        elif ans_len > 200:
            score += 1

        # 规则 2: 错误关键词
        error_keywords = ["抱歉", "不可用", "服务异常", "暂时无法", "出错了", "失败了"]
        error_count = sum(1 for kw in error_keywords if kw in final_answer)
        if error_count >= 2:
            score -= 3
            reasons.append("包含多个错误关键词")
        elif error_count >= 1:
            score -= 1
            reasons.append("包含错误关键词")

        # 规则 3: 工具使用
        if tools_used:
            score += 1
            tool_ref_keywords = ["根据", "检索", "查询", "搜索", "工具", "返回", "结果显示"]
            has_tool_ref = any(kw in final_answer for kw in tool_ref_keywords)
            if has_tool_ref:
                score += 1
            else:
                score -= 1
                reasons.append("使用了工具但未引用结果")

        # 规则 4: 记忆引用
        if memory_ctx.get("count", 0) > 0:
            mem_ref_keywords = ["之前", "上次", "记得", "历史", "记忆"]
            has_mem_ref = any(kw in final_answer for kw in mem_ref_keywords)
            if has_mem_ref:
                score += 1

        # 规则 5: 结构化检查
        struct_markers = ["\n-", "\n*", "\n1.", "\n2.", "##", "**"]
        has_structure = any(m in final_answer for m in struct_markers)
        if has_structure:
            score += 1

        # 规则 6: 不确定性标注
        uncertainty_markers = ["可能", "也许", "据我了解", "不确定", "推测"]
        has_uncertainty = any(m in final_answer for m in uncertainty_markers)
        if has_uncertainty:
            score += 0.5

        # 规则 7: 工具调用 JSON 残留检测（回答里混入了工具调用格式）
        tool_json_markers = ['"name":', '"parameters":', '"query":', "web_search", "search_web", "function_call"]
        tool_json_count = sum(1 for m in tool_json_markers if m in final_answer)
        if tool_json_count >= 2:
            score -= 4
            reasons.append("回答包含工具调用残留")
        elif tool_json_count >= 1:
            score -= 2
            reasons.append("回答可能包含工具调用残留")

        # 规则 8: 自然语言比例检测（中文字符占比）
        if ans_len >= 20:
            chinese_chars = sum(1 for c in final_answer if '\u4e00' <= c <= '\u9fff')
            cn_ratio = chinese_chars / ans_len
            if cn_ratio < 0.1 and ans_len > 50:
                score -= 3
                reasons.append("回答缺少自然语言内容")

        return max(1, min(10, int(score))), reasons

    # ── Phase 2: LLM-as-Judge ──
    _EVALUATOR_PROMPT = """你是一个严格的质量评估员。请评估以下 AI 回答的质量。

用户问题:
{question}

AI 回答:
{answer}

评估维度（每项 1-10 分）:
1. 相关性 — 回答是否针对用户问题
2. 准确性 — 信息是否正确
3. 完整性 — 是否充分回答了问题
4. 可读性 — 是否是通顺的自然语言

请严格按以下 JSON 格式返回（不要返回其他内容）:
{{"score": <1-10>, "reason": "<简短评估理由>", "passed": <true/false>}}

通过标准: score >= 6"""

    async def _llm_judge(final_answer: str, user_question: str) -> dict | None:
        """调用 LLM 做语义评估，失败返回 None（降级为规则结果）。"""
        if not llm:
            return None
        try:
            prompt = _EVALUATOR_PROMPT.format(question=user_question, answer=final_answer[:2000])
            resp = await llm.ainvoke([HumanMessage(content=prompt)])
            content = _content_to_str(getattr(resp, "content", ""))
            # 尝试从回复中提取 JSON
            import re
            json_match = re.search(r'\{[^{}]*\}', content)
            if json_match:
                import json as _json
                return _json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"[evaluator] LLM 评估失败，降级为规则: {e}")
        return None

    def _extract_user_question(state: AgentState) -> str:
        """从消息历史中提取用户第一个问题。"""
        messages = state.get("messages", [])
        for m in messages:
            role = getattr(m, "role", "") if not isinstance(m, dict) else m.get("role", "")
            if role == "user":
                content = getattr(m, "content", "") if not isinstance(m, dict) else m.get("content", "")
                return _content_to_str(content)[:500]
        return ""

    async def evaluator_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        final_answer = state.get("final_answer", "")
        if not final_answer:
            writer({"step": "eval", "status": "skipped", "message": "无回答，跳过评估"})
            logger.info("[evaluator] 无回答，跳过评估")
            return {"evaluation": {"passed": False, "reason": "无回答", "score": 0}}

        writer({"step": "eval", "status": "checking", "message": "正在评估回答质量..."})
        logger.info("[evaluator] 开始评估回答质量")

        tools_used = state.get("tools_used", [])
        memory_ctx = state.get("memory_context") or {}

        # ── Phase 1: 增强规则评分 ──
        rule_score, reasons = _rule_based_score(final_answer, tools_used, memory_ctx)
        logger.info(f"[evaluator] 规则评分: {rule_score}/10, reasons={reasons}")

        # ── Phase 2: 边界 case 调用 LLM 评估 ──
        final_score = rule_score
        final_reasons = reasons
        used_llm = False

        if 5 <= rule_score <= 8 and llm:
            user_question = _extract_user_question(state)
            if user_question:
                writer({"step": "eval", "status": "checking", "message": "规则评分边界，调用 LLM 精细评估..."})
                llm_result = await _llm_judge(final_answer, user_question)
                if llm_result and "score" in llm_result:
                    llm_score = int(llm_result["score"])
                    llm_passed = llm_result.get("passed", llm_score >= 6)
                    llm_reason = llm_result.get("reason", "")
                    used_llm = True
                    # LLM 评估与规则评估加权平均（LLM 权重更高）
                    final_score = max(1, min(10, int(rule_score * 0.3 + llm_score * 0.7)))
                    if llm_reason:
                        final_reasons = [f"LLM: {llm_reason}"] + reasons
                    logger.info(f"[evaluator] LLM 评分: {llm_score}/10, 综合: {final_score}/10")

        passed = final_score >= 6
        reason = "、".join(final_reasons) if final_reasons else "质量合格"

        evaluation = {
            "score": final_score,
            "passed": passed,
            "reason": reason,
            "dimensions": {
                "accuracy": final_score,
                "completeness": final_score,
                "hallucination": final_score,
                "tool_usage": final_score,
                "memory_usage": final_score,
            },
            "method": "llm_judge" if used_llm else "rule_based",
        }

        if passed:
            writer({"step": "eval", "status": "done", "message": f"质量评估通过 ({final_score}/10)", "score": final_score})
            logger.info(f"[evaluator] 质量评估通过 ({final_score}/10, method={evaluation['method']})")
        else:
            writer({"step": "eval", "status": "done", "message": f"质量评估未通过 ({final_score}/10, {reason})", "score": final_score})
            logger.info(f"[evaluator] 质量评估未通过 ({final_score}/10, {reason}, method={evaluation['method']})")

        # 评估只打分，不替换 LLM 回答
        return {"evaluation": evaluation}

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

        # LangGraph 官方模式：错误不存入记忆，避免污染对话历史
        if state.get("is_error"):
            writer({"step": "memory_save", "status": "skipped", "message": "错误响应，跳过记忆保存"})
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
    """goal_evaluator 之后的路由 — 达成/超限/阻塞→结束，未达成→重试"""
    status = state.get("goal_status", "")
    if status in ("achieved", "budget_exceeded", "failed", "blocked"):
        return END
    return "model_selector"


def _after_goal_replan(state: AgentState) -> str:
    """goal_replanner 之后的路由 — 达成直接保存记忆，不再重复评估"""
    status = state.get("goal_status", "")
    if status == "achieved":
        return "memory_saver"
    if status in ("budget_exceeded", "failed", "blocked"):
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


