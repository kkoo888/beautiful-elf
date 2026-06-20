"""Agent 引擎 — LangGraph StateGraph 驱动（v4.0 重构版）

v4.0 重构清单:
  1. interrupt/resume 正式启用（持久化 checkpointer + resume API 支持）
  2. LLM-as-Judge 评估器（替代纯规则评估）
  3. 熔断器（CircuitBreaker）防止级联故障
  4. 工具并行执行（无依赖工具 asyncio.gather）
  5. Context 压缩策略（LLM 驱动的智能压缩）
  6. RAG Query Rewriting（检索前改写口语化查询）
  7. 记忆摘要优化（结构化标签 + 重要性评分）
  8. Streaming 输出钩子预留
  9. Error Contract 三级分类
  10. 全链路可观测 + trace 回放
"""
from typing import Annotated, Optional, List, Dict, Any, Callable
import operator
import time
import json
import asyncio
import os

from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from app.core.logging import get_logger
from app.agent.context_engine import MAX_CONTEXT_CHARS
from app.agent.state import AgentState, InputState, OutputState, Context, _content_blocks_to_str

logger = get_logger(__name__)

MAX_MESSAGE_WINDOW = 30
DEFAULT_AGENT_TIMEOUT = 300  # 全局超时 5 分钟


# ── 熔断器 ────────────────────────────────────────────────

class CircuitBreaker:
    """简单熔断器 — 防止工具级联故障

    三态：closed（正常）→ open（熔断，快速失败）→ half-open（试探恢复）
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self._failure_count: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._state: Dict[str, str] = {}  # tool_name -> state
        self._threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

    def is_available(self, tool_name: str) -> bool:
        """工具是否可用"""
        state = self._state.get(tool_name, "closed")
        if state == "closed":
            return True
        if state == "open":
            # 检查是否到了恢复时间
            elapsed = time.time() - self._last_failure_time.get(tool_name, 0)
            if elapsed >= self._recovery_timeout:
                self._state[tool_name] = "half-open"
                logger.info(f"[circuit_breaker] {tool_name} 进入 half-open 状态，试探恢复")
                return True
            return False
        # half-open 状态允许一次尝试
        return True

    def record_success(self, tool_name: str):
        """记录成功"""
        self._failure_count[tool_name] = 0
        self._state[tool_name] = "closed"

    def record_failure(self, tool_name: str):
        """记录失败"""
        count = self._failure_count.get(tool_name, 0) + 1
        self._failure_count[tool_name] = count
        self._last_failure_time[tool_name] = time.time()

        if count >= self._threshold:
            self._state[tool_name] = "open"
            logger.warning(f"[circuit_breaker] {tool_name} 熔断！连续失败 {count} 次，{self._recovery_timeout}s 后恢复")

    def get_state(self, tool_name: str) -> str:
        return self._state.get(tool_name, "closed")


# 全局熔断器实例
_circuit_breaker = CircuitBreaker()


# ── 持久化 Checkpointer ───────────────────────────────────

def _create_checkpointer():
    """创建持久化 checkpointer（优先 SQLite，降级内存）"""
    db_path = os.getenv("CHECKPOINTER_DB_PATH", "/tmp/agent_checkpoints.db")
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        logger.info(f"[checkpointer] 使用 SQLite 持久化: {db_path}")
        return AsyncSqliteSaver.from_conn_string(db_path)
    except ImportError:
        logger.warning("[checkpointer] sqlite 模块不可用，降级为内存版（重启丢失状态）")
        return MemorySaver()


# ── 状态定义 ──────────────────────────────────────────────

# AgentState 已迁移到 state.py（Pydantic BaseModel，2026 行业标准）
# 见: app/agent/state.py


# ── 错误契约 ──────────────────────────────────────────────

class ErrorContract:
    @staticmethod
    def retryable(tool_name: str, error: str, attempt: int) -> dict:
        return {"success": False, "error": {"code": "TOOL_TRANSIENT_ERROR", "message": f"工具 {tool_name} 暂时不可用: {error}", "retryable": True, "user_facing": False, "attempt": attempt}}

    @staticmethod
    def user_facing(tool_name: str, error: str, user_tip: str) -> dict:
        return {"success": False, "error": {"code": "TOOL_USER_ERROR", "message": f"工具 {tool_name}: {error}", "retryable": False, "user_facing": True, "user_tip": user_tip}}

    @staticmethod
    def escalate(tool_name: str, error: str) -> dict:
        return {"success": False, "error": {"code": "TOOL_SYSTEM_ERROR", "message": f"工具 {tool_name} 系统异常: {error}", "retryable": False, "user_facing": False, "escalate": True}}


# ── 构建图 ────────────────────────────────────────────────

def build_agent_graph(
    llm,
    tool_registry,
    context_engine=None,
    memory_manager=None,
    intent_router=None,
    skill_executor=None,
    rag_pipeline=None,
    model_selector=None,
    enable_interrupt: bool = False,
    timeout_seconds: int = DEFAULT_AGENT_TIMEOUT,
) -> Any:
    """
    构建 Agent 工作流图。

    v6.0 变更（P0-P3 升级）:
      - P0: 跨线程长期记忆（MySQL CrossThreadMemory）
      - P1: context_schema (Context) — 运行时数据与状态解耦
      - P1: InputState / OutputState — 输入输出约束
      - P2: Checkpointer 持久化 — time travel + fault tolerance

    v5.3 变更:
      - model_selector ML 模型路由

    Args:
        enable_interrupt: 是否启用 interrupt/resume（需要 checkpointer）
        timeout_seconds: 全局超时（秒），超时后 Agent 强制结束
    """
    graph = StateGraph(AgentState, input=InputState, output=OutputState, context_schema=Context)

    # 模型路由（入口节点，在意图路由之前）
    graph.add_node("model_selector", _make_model_selector_node(model_selector))
    graph.add_node("intent_router", _make_intent_router(intent_router))
    graph.add_node("skill_executor", _make_skill_executor_node(skill_executor, context_engine, memory_manager))
    graph.add_node("context_builder", _make_context_builder(context_engine, memory_manager, tool_registry))
    graph.add_node("llm_call", _make_llm_caller(llm, tool_registry, model_selector))
    graph.add_node("tool_executor", _make_tool_executor(tool_registry))
    graph.add_node("approval_node", _make_approval_node(tool_registry))
    graph.add_node("evaluator", _make_evaluator_node(llm))
    graph.add_node("memory_saver", _make_memory_saver(memory_manager))
    goal_evaluator = _make_goal_evaluator(llm)
    goal_status_updater = _make_goal_status_updater()
    goal_replanner = _make_goal_replanner(llm)
    graph.add_node("goal_evaluator", goal_evaluator)
    graph.add_node("goal_status_updater", goal_status_updater)
    graph.add_node("goal_replanner", goal_replanner)

    # 入口: model_selector → intent_router → ...
    graph.set_entry_point("model_selector")
    graph.add_edge("model_selector", "intent_router")
    graph.add_conditional_edges("intent_router", _route_after_intent, {
        "skill": "skill_executor",
        "agent": "context_builder",
        "cache_return": "memory_saver",
    })
    graph.add_edge("skill_executor", "memory_saver")
    graph.add_edge("context_builder", "llm_call")
    graph.add_conditional_edges("llm_call", _should_use_tools, {
        "use_tools": "tool_executor",
        "finish": "evaluator",
    })
    graph.add_conditional_edges("tool_executor", _after_tool_exec, {
        "needs_approval": "approval_node",
        "continue": "llm_call",
    })
    graph.add_conditional_edges("approval_node", _after_approval, {
        "approved": "llm_call",
        "rejected": "memory_saver",
    })
    graph.add_conditional_edges("evaluator", _after_eval, {
        "pass": "memory_saver",
        "replan": "llm_call",
    })
    # memory_saver 之后：Goal 模式走状态更新器
    graph.add_conditional_edges("memory_saver", _after_memory, {
        "goal_status_updater": "goal_status_updater",
        END: END,
    })
    graph.add_edge("goal_status_updater", "goal_replanner")
    graph.add_conditional_edges("goal_replanner", _after_goal_replan, {
        "goal_evaluator": "goal_evaluator",
        "model_selector": "model_selector",
        END: END,
    })
    graph.add_conditional_edges("goal_evaluator", _after_goal_eval, {
        END: END,
        "model_selector": "model_selector",
    })

    checkpointer = _create_checkpointer() if enable_interrupt else MemorySaver()
    compile_kwargs = {"checkpointer": checkpointer}
    if enable_interrupt:
        compile_kwargs["interrupt_before"] = ["approval_node"]
    return graph.compile(**compile_kwargs)


# ── 节点工厂 ──────────────────────────────────────────────

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

                # ── 第0轮：规划阶段（纯文本输出，不调用工具）──
                system_prompt = f"""{system_prompt}

══════════════════════════════════════════════════
【目标驱动模式 — 第0轮：规划】
══════════════════════════════════════════════════

## 目标
{goal_def}

## 你的唯一任务
分析目标，制定一个分步执行计划。如果每个步骤都正确执行，最终将得出正确答案。

## 规划原则（LangGraph Plan-and-Execute 官方规范）
1. 不要添加任何多余的步骤 — 每个步骤都必须是达成目标的必要条件
2. 确保每个步骤包含所需的所有信息 — 不要跳过步骤
3. 最后一个步骤的结果应为最终答案
4. 每个步骤必须是可通过一次工具调用完成的原子操作
5. 每个步骤必须有明确的成功标准（输出什么、验证什么）

## 输出格式（必须严格遵循，前端依赖此格式解析）
[目标拆解]
• [子任务描述] - [pending] (0%)
• [子任务描述] - [pending] (0%) -> 依赖: 1
• [子任务描述] - [pending] (0%) -> 依赖: 1,2

## 格式规则
- 每行一个子任务，以 • 开头
- [pending] = 待执行状态，(0%) = 初始进度
- -> 依赖: N = 需要第N个子任务完成后才能开始（可选）

## 约束
- 本阶段只输出计划，不要执行任何操作
- 不要输出承诺性语句
- 直接输出计划，不要有前言或解释"""
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

## 执行方式（ReAct 模式）
对当前子任务，按以下步骤执行：
Thought: 分析需要调用什么工具，为什么
Action: 调用工具获取真实数据
Observation: 检查工具返回结果
Answer: 基于结果输出该子任务的成果

## 核心规则
1. **工具优先** — 先尝试调用工具获取实时数据；工具不可用时基于已有知识降级回答，注明"（降级回答）"
2. **只做一件事** — 只执行上面列出的当前子任务，不要跳到其他任务
3. **完成后标记** — 输出: • [子任务描述] - [done] (100%)

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

        # Goal 模式: 跳过常规评估
        if state.get("goal_mode"):
            writer({"step": "eval", "status": "skipped", "message": "Goal 模式，跳过常规评估"})
            return {"evaluation": {"passed": True, "reason": "goal_mode_skip", "score": 8},
                    "iterations": state.get("iterations", 0) + 1}

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


def _make_goal_evaluator(llm):
    """Goal 模式评估器 — 判断目标是否达成"""

    async def goal_evaluator(state: dict) -> dict:
        """评估当前结果是否达成目标"""
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()
        from app.core.logging import get_logger as _get_logger
        _logger = _get_logger(__name__)

        goal = state.get("goal_definition", "")
        final_answer = state.get("final_answer", "")
        iterations = state.get("goal_iterations", 0)
        max_iterations = state.get("goal_max_iterations", 5)
        tokens_used = state.get("goal_tokens_used", 0)
        token_budget = state.get("goal_token_budget", 50000)

        # Token 预算检查
        if tokens_used >= token_budget:
            writer({"step": "goal_eval", "status": "done", "message": "已达 Token 预算上限"})
            return {"goal_status": "budget_exceeded"}

        # 最大迭代检查
        if iterations >= max_iterations:
            writer({"step": "goal_eval", "status": "done", "message": "已达最大迭代次数"})
            return {"goal_status": "failed"}

        # 如果没有 final_answer，说明还没执行过
        if not final_answer:
            return {"goal_status": "in_progress", "goal_iterations": iterations + 1}

        # LLM 评估是否达成目标
        eval_prompt = f"""你是一个目标评估器。判断以下回答是否达成了用户的目标。

用户目标：{goal}

当前回答：{final_answer[:2000]}

评估说明：
1. 优先评估回答内容是否实质上回答了用户的问题
2. 如果回答中包含"基于已有知识"、"工具不可用时的降级回答"等说明，且内容合理准确，应视为有效回答
3. 工具调用失败时的降级回答（基于大模型知识）是可接受的
4. 只有当回答完全无关、空白或明显错误时才判定为未达成

请严格按 JSON 格式输出：
{{"achieved": true/false, "reason": "原因", "suggestion": "如果未达成，下一步建议"}}

只输出 JSON，不要其他文字。"""

        try:
            response = await llm.ainvoke(eval_prompt)
            content = _content_blocks_to_str(response.content if hasattr(response, 'content') else response)
            import re
            match = re.search(r'\{.*?\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                achieved = data.get("achieved", False)

                if achieved:
                    writer({"step": "goal_eval", "status": "done", "message": "目标已达成！"})
                    # Self-Healing: 标记反思成功
                    try:
                        from app.agent.self_healing import get_healing_memory
                        healing_memory = get_healing_memory()
                        for st in (state.get("goal_subtasks") or []):
                            if st.get("status") == "done":
                                await healing_memory.mark_successful(
                                    user_id=state.get("user_id", 0), subtask_id=st.get("id", 0))
                    except Exception:
                        pass
                    return {"goal_status": "achieved"}
                else:
                    history = list(state.get("goal_history", []))
                    history.append({
                        "iteration": iterations,
                        "result": final_answer[:500],
                        "evaluation": data.get("reason", ""),
                        "suggestion": data.get("suggestion", ""),
                    })
                    writer({"step": "goal_eval", "status": "done",
                            "message": f"目标未达成 (第{iterations+1}轮): {data.get('reason', '')[:50]}"})
                    return {
                        "goal_status": "in_progress",
                        "goal_iterations": iterations + 1,
                        "goal_history": history,
                        "goal_current_plan": data.get("suggestion", ""),
                    }
        except Exception as e:
            _logger.warning(f"[goal_evaluator] 评估失败: {e}")

        return {"goal_status": "in_progress", "goal_iterations": iterations + 1}

    return goal_evaluator

def _make_goal_status_updater():
    """Goal 模式子任务状态更新器"""

    async def goal_status_updater_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        if state.get("goal_iterations", 0) == 0:
            _loop_detector.reset()

        goal_subtasks = list(state.get("goal_subtasks") or [])
        if not goal_subtasks:
            return {}

        final_answer = state.get("final_answer", "")
        answer_text = _content_to_str(final_answer) if final_answer else ""

        # 找到当前正在执行的子任务
        current_subtask = None
        for st in goal_subtasks:
            if st.get("status") == "in_progress":
                current_subtask = st
            elif not current_subtask and st.get("status") == "pending":
                done_ids = {t["id"] for t in goal_subtasks if t.get("status") == "done"}
                deps = st.get("dependencies", [])
                if all(d in done_ids for d in deps):
                    current_subtask = st

        # Guardrail 校验 + Self-Healing
        if current_subtask:
            task_id = current_subtask["id"]
            passed, reason = _guardrail_check_subtask(answer_text, current_subtask["title"])
            if passed:
                goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "done", 100)
                _loop_detector.record(task_id, "done")
                writer({"step": "goal_task_done", "status": "done",
                        "message": f"子任务完成: {current_subtask['title']}",
                        "taskId": task_id, "taskTitle": current_subtask["title"]})
                logger.info(f"[goal_status_updater] 子任务 #{task_id} → done")
            else:
                goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "failed", 0)
                try:
                    from app.agent.self_healing import analyze_failure, get_healing_memory
                    reflection = analyze_failure(
                        subtask_title=current_subtask["title"], subtask_id=task_id,
                        failure_source="guardrail", answer_text=answer_text,
                        guardrail_reason=reason,
                        user_id=state.get("user_id", 0),
                        goal_definition=state.get("goal_definition", ""),
                    )
                    await get_healing_memory().store(reflection, goal_id=str(state.get("conversation_id", 0)))
                    _loop_detector.record(task_id, "failed")
                    is_loop, loop_reason = _loop_detector.is_looping()
                    if is_loop:
                        writer({"step": "loop_detected", "status": "error",
                                "message": f"检测到循环: {loop_reason}"})
                except Exception as e:
                    logger.debug(f"[goal_status_updater] 自愈分析跳过: {e}")
                writer({"step": "goal_task_failed", "status": "error",
                        "message": f"子任务未通过校验: {current_subtask['title']} ({reason})",
                        "taskId": task_id, "taskTitle": current_subtask["title"]})

        # 批量标记可并行的子任务
        parallel_tasks = _get_parallel_ready_tasks(goal_subtasks)
        if parallel_tasks:
            for task in parallel_tasks:
                goal_subtasks = _update_subtask_status(goal_subtasks, task["id"], "in_progress", 0)
                writer({"step": "goal_task_start", "status": "executing",
                        "message": f"开始执行: {task['title']}",
                        "taskId": task["id"], "taskTitle": task["title"]})

        writer({"step": "goal_subtasks", "status": "done",
                "message": "子任务状态更新", "subtasks": goal_subtasks})
        return {"goal_subtasks": goal_subtasks}

    return goal_status_updater_node


def _make_goal_replanner(llm):
    """Goal 模式 Re-planner"""

    async def goal_replanner_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        goal_def = state.get("goal_definition", "")
        goal_subtasks = list(state.get("goal_subtasks") or [])
        iterations = state.get("goal_iterations", 0)
        max_iterations = state.get("goal_max_iterations", 5)
        tokens_used = state.get("goal_tokens_used", 0)
        token_budget = state.get("goal_token_budget", 50000)
        goal_history = list(state.get("goal_history") or [])

        done_count = sum(1 for t in goal_subtasks if t.get("status") == "done")
        failed_count = sum(1 for t in goal_subtasks if t.get("status") == "failed")
        total = len(goal_subtasks)

        # Token 预算 + 成本预估
        avg_tokens = tokens_used / max(done_count, 1) if done_count > 0 else 5000
        remaining_tasks = sum(1 for t in goal_subtasks if t.get("status") == "pending")
        estimated_remaining = int(avg_tokens * remaining_tasks)

        if tokens_used >= token_budget:
            writer({"step": "goal_replan", "status": "done", "message": "已达 Token 预算上限"})
            return {"goal_status": "budget_exceeded"}

        if iterations >= max_iterations:
            writer({"step": "goal_replan", "status": "done", "message": f"已达最大迭代次数 ({max_iterations})"})
            return {"goal_status": "failed"}

        # 全部完成
        if done_count == total and total > 0:
            writer({"step": "goal_replan", "status": "done", "message": f"所有子任务已完成 ({done_count}/{total})"})
            return {"goal_status": "achieved"}

        # 有失败 → 生成自愈反思
        failed_tasks = [t for t in goal_subtasks if t.get("status") == "failed"]
        if failed_tasks:
            try:
                from app.agent.self_healing import analyze_failure, get_healing_memory
                healing_memory = get_healing_memory()
                goal_id = str(state.get("conversation_id", 0))
                for ft in failed_tasks:
                    reflection = analyze_failure(
                        subtask_title=ft.get("title", ""), subtask_id=ft.get("id", 0),
                        failure_source="eval", error_message="子任务执行失败",
                        user_id=state.get("user_id", 0), goal_definition=goal_def,
                    )
                    reflection.retry_count = iterations
                    await healing_memory.store(reflection, goal_id=goal_id)
            except Exception as e:
                logger.debug(f"[goal_replanner] 自愈反思跳过: {e}")

        # 所有任务已处理但未全部完成
        pending_tasks = [t for t in goal_subtasks if t.get("status") == "pending"]
        if not pending_tasks and done_count < total:
            return {"goal_status": "failed", "goal_iterations": iterations + 1, "goal_subtasks": goal_subtasks}

        writer({"step": "goal_replan", "status": "done",
                "message": f"继续执行 ({done_count}/{total} 完成, 第{iterations+1}轮)"})
        return {
            "goal_status": "in_progress",
            "goal_iterations": iterations + 1,
            "goal_subtasks": goal_subtasks,
            "goal_history": goal_history + [{
                "iteration": iterations,
                "result": f"{done_count}/{total} done, {failed_count} failed",
                "evaluation": "需要继续执行",
                "suggestion": f"还有 {len(pending_tasks)} 个子任务待执行",
            }],
        }

    return goal_replanner_node



# ── 条件路由 ──────────────────────────────────────────────

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
    """memory_saver 之后的路由 — Goal 模式走状态更新器，否则结束"""
    if state.get("goal_mode"):
        return "goal_status_updater"
    return END


def _after_goal_eval(state: AgentState) -> str:
    """goal_evaluator 之后的路由 — 达成/超限→结束，未达成→重试"""
    status = state.get("goal_status", "")
    if status in ("achieved", "budget_exceeded", "failed"):
        return END
    return "model_selector"


def _after_goal_replan(state: AgentState) -> str:
    """goal_replanner 之后的路由"""
    status = state.get("goal_status", "")
    if status == "achieved":
        return "goal_evaluator"
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


def _parse_goal_subtasks(text: str) -> list:
    """从 LLM 回复中解析 [目标拆解] 格式的子任务列表。

    格式示例：
        [目标拆解]
        • 搜索 Loop Engineering 公司信息 - [pending] (0%)
        • 分析技术路线 - [pending] (0%) -> 依赖: 1
    """
    import re
    tasks = []
    match = re.search(r'\[目标拆解\]\s*\n([\s\S]*?)(?=\n\n|═|$)', text)
    if not match:
        return tasks

    lines = match[1].split('\n')
    task_id = 0
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        task_match = re.match(
            r'^[•\-\d\.]+\s*(.+?)\s*-\s*\[(pending|in_progress|done|failed)\](?:\s*\((\d+)%\))?(?:\s*->\s*依赖:\s*([\d,\s]+))?',
            trimmed
        )
        if task_match:
            task_id += 1
            title = task_match[1].strip()
            status_str = task_match[2]
            progress = int(task_match[3]) if task_match[3] else 0
            deps_str = task_match[4]
            dependencies = [int(d.strip()) for d in deps_str.split(',') if d.strip().isdigit()] if deps_str else []
            tasks.append({
                "id": task_id,
                "title": title,
                "status": status_str,
                "progress": progress,
                "dependencies": dependencies,
            })
    return tasks



# ── 循环检测器 ─────────────────────────────────────────────

class LoopDetector:
    """检测同一子任务连续失败，防止死循环"""
    def __init__(self, max_consecutive: int = 3):
        self._history: list[tuple[int, str]] = []
        self._max = max_consecutive

    def record(self, subtask_id: int, status: str):
        self._history.append((subtask_id, status))
        if len(self._history) > self._max * 2:
            self._history = self._history[-self._max * 2:]

    def is_looping(self) -> tuple:
        if len(self._history) < self._max:
            return False, ""
        recent = self._history[-self._max:]
        ids = [r[0] for r in recent]
        statuses = [r[1] for r in recent]
        if len(set(ids)) == 1 and all(s == "failed" for s in statuses):
            return True, f"子任务 #{ids[0]} 连续失败 {self._max} 次"
        return False, ""

    def get_stuck_task_id(self):
        if len(self._history) < self._max:
            return None
        recent = self._history[-self._max:]
        ids = [r[0] for r in recent]
        statuses = [r[1] for r in recent]
        if len(set(ids)) == 1 and all(s == "failed" for s in statuses):
            return ids[0]
        return None

    def reset(self):
        self._history.clear()


_loop_detector = LoopDetector()


# ── 输入校验 ───────────────────────────────────────────────

def _validate_goal_definition(goal_definition: str) -> tuple:
    """Goal 定义前置校验"""
    if not goal_definition or not goal_definition.strip():
        return False, "目标定义不能为空"
    cleaned = goal_definition.strip()
    if len(cleaned) < 10:
        return False, f"目标定义过短（{len(cleaned)} 字符），至少需要 10 个字符"
    if len(cleaned) > 2000:
        return False, f"目标定义过长（{len(cleaned)} 字符），请精简到 2000 字符以内"
    meaningful = re.sub(r'[?!？！.。，,\s]+', '', cleaned)
    if len(meaningful) < 5:
        return False, "目标定义缺少实质内容，请描述具体要做什么"
    return True, ""


# ── 子任务辅助函数 ─────────────────────────────────────────

def _get_next_pending_subtask(goal_subtasks: list) -> "dict | None":
    """获取下一个待执行子任务（DAG 拓扑排序）"""
    if not goal_subtasks:
        return None
    done_ids = {t["id"] for t in goal_subtasks if t.get("status") == "done"}
    for task in goal_subtasks:
        if task.get("status") != "pending":
            continue
        deps = task.get("dependencies", [])
        if all(d in done_ids for d in deps):
            return task
    for task in goal_subtasks:
        if task.get("status") == "pending":
            return task
    return None


def _get_parallel_ready_tasks(goal_subtasks: list, max_parallel: int = 3) -> list:
    """获取可并行执行的 pending 子任务"""
    if not goal_subtasks:
        return []
    done_ids = {t["id"] for t in goal_subtasks if t.get("status") == "done"}
    ready = []
    for task in goal_subtasks:
        if task.get("status") != "pending":
            continue
        deps = task.get("dependencies", [])
        if all(d in done_ids for d in deps):
            ready.append(task)
        if len(ready) >= max_parallel:
            break
    return ready


def _update_subtask_status(goal_subtasks: list, task_id: int, status: str, progress: int = 0) -> list:
    """更新指定子任务状态"""
    return [
        {**t, "status": status, "progress": progress} if t.get("id") == task_id else t
        for t in goal_subtasks
    ]


def _build_goal_progress_text(goal_subtasks: list) -> str:
    """构建进度文本"""
    if not goal_subtasks:
        return ""
    done = [t for t in goal_subtasks if t.get("status") == "done"]
    failed = [t for t in goal_subtasks if t.get("status") == "failed"]
    in_progress = [t for t in goal_subtasks if t.get("status") == "in_progress"]
    pending = [t for t in goal_subtasks if t.get("status") == "pending"]
    lines = []
    if done:
        lines.append("### ✅ 已完成")
        for t in done:
            lines.append(f"  ✅ #{t['id']} {t['title']}")
    if failed:
        lines.append("### ❌ 失败")
        for t in failed:
            lines.append(f"  ❌ #{t['id']} {t['title']}")
    if in_progress:
        lines.append("### 🔄 执行中")
        for t in in_progress:
            lines.append(f"  🔄 #{t['id']} {t['title']}")
    if pending:
        lines.append("### ⏳ 待执行")
        for t in pending:
            deps = t.get('dependencies', [])
            dep_str = f" (依赖: {','.join(str(d) for d in deps)})" if deps else ""
            lines.append(f"  ⏳ #{t['id']} {t['title']}{dep_str}")
    return "\n".join(lines)


# ── Guardrail 校验 ─────────────────────────────────────────

def _guardrail_check_subtask(answer_text: str, subtask_title: str) -> tuple:
    """子任务输出 Guardrail 校验"""
    if not answer_text or len(answer_text.strip()) < 20:
        return False, "输出内容过短或为空"
    failure_markers = ["抱歉", "无法", "失败", "错误", "不可用", "unable", "error", "failed"]
    marker_count = sum(1 for m in failure_markers if m in answer_text)
    if marker_count >= 3 and len(answer_text) < 100:
        return False, f"输出包含多个失败标记 ({marker_count} 个)"
    promise_patterns = [r"^我来帮你", r"^让我", r"^我将要", r"^接下来我会"]
    for pattern in promise_patterns:
        if re.match(pattern, answer_text.strip()):
            return False, "输出为承诺性回复，缺少实质内容"
    return True, ""


def _content_to_str(content) -> str:
    """将消息 content 统一转为字符串。委托给 state._content_blocks_to_str。"""
    return _content_blocks_to_str(content)


def _build_message_dicts(state) -> List[dict]:
    result = []
    for m in state.get("messages", []):
        if isinstance(m, dict):
            result.append({"role": m.get("role", "user"), "content": _content_to_str(m.get("content", ""))})
        else:
            result.append({"role": getattr(m, "role", "user"), "content": _content_to_str(getattr(m, "content", ""))})
    return result


def _trim_messages(messages: list, max_count: int) -> list:
    if len(messages) <= max_count:
        return messages
    trimmed = messages[-max_count:]
    logger.info(f"[message_trim] {len(messages)} → {len(trimmed)} 条消息")
    return trimmed


def _format_tool_result_json(result: Any, tool_name: str, last_error: str = None) -> str:
    """格式化工具结果为 JSON 字符串（MCP 规范: content[text] 序列化 JSON）

    MCP 规范要求工具返回:
      - content: [{"type": "text", "text": "序列化JSON"}]
      - structuredContent: {结构化对象}（可选，需要 outputSchema）
    这里统一输出序列化 JSON 字符串，符合 MCP content[text] 格式。
    """
    if result is None:
        return json.dumps(ErrorContract.retryable(tool_name, last_error or "未知错误", attempt=2), ensure_ascii=False)
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, default=str)
    if isinstance(result, (list, tuple)):
        return json.dumps(result, ensure_ascii=False, default=str)
    return json.dumps({"result": str(result)}, ensure_ascii=False)
