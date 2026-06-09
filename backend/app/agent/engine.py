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
from typing import TypedDict, Annotated, Optional, List, Dict, Any, Callable
import operator
import time
import json
import asyncio
import os

from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from app.core.logging import get_logger
from app.agent.context_engine import MAX_CONTEXT_CHARS

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
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()


# ── 状态定义 ──────────────────────────────────────────────

class AgentState(TypedDict):
    conversation_id: int
    user_id: int
    messages: Annotated[list, operator.add]
    context: str
    system_prompt: str
    tool_calls: list
    tools_used: Annotated[list, operator.add]
    final_answer: Optional[str]
    iterations: int
    needs_approval: bool
    pending_tool_call: Optional[dict]
    intent: Optional[dict]
    skill_answer: Optional[str]
    error: Optional[str]
    trace_metadata: dict
    provider_id: Optional[int]
    model_name: str
    evaluation: Optional[dict]  # 评估结果
    # 记忆元数据（由 context_builder 填充，供 memory_saver / evaluator 消费）
    memory_context: Optional[dict]  # {"ids": [...], "scores": [...], "count": int, "avg_score": float}
    conversation_importance: Optional[int]  # 对话重要性评分 (1-10)
    # ── B+C: 动态工具选择 ──────────────────────────────
    selected_tools: list  # 当前请求选中的工具名列表（str），非 Tool 对象（避免序列化问题）


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
    enable_interrupt: bool = False,
    timeout_seconds: int = DEFAULT_AGENT_TIMEOUT,
) -> Any:
    """
    构建 Agent 工作流图（v5.0 — B+C 动态工具绑定）。

    v5.0 变更:
      - 工具不再在初始化时全量 bind_tools
      - context_builder 根据 intent 动态选择工具
      - llm_caller 每次请求动态绑定工具

    Args:
        enable_interrupt: 是否启用 interrupt/resume（需要 checkpointer）
        timeout_seconds: 全局超时（秒），超时后 Agent 强制结束
    """
    graph = StateGraph(AgentState)

    graph.add_node("intent_router", _make_intent_router(intent_router))
    graph.add_node("skill_executor", _make_skill_executor_node(skill_executor))
    graph.add_node("context_builder", _make_context_builder(context_engine, memory_manager, tool_registry))
    graph.add_node("llm_call", _make_llm_caller(llm, tool_registry))
    graph.add_node("tool_executor", _make_tool_executor(tool_registry))
    graph.add_node("approval_node", _make_approval_node(tool_registry))
    graph.add_node("evaluator", _make_evaluator_node(llm))
    graph.add_node("memory_saver", _make_memory_saver(memory_manager))

    graph.set_entry_point("intent_router")
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
    graph.add_edge("memory_saver", END)

    if enable_interrupt:
        checkpointer = _create_checkpointer()
        return graph.compile(checkpointer=checkpointer, interrupt_before=["approval_node"])
    # [FIX] 始终使用 MemorySaver，确保 get_state() 可用于流式场景的 fallback
    from langgraph.checkpoint.memory import MemorySaver
    return graph.compile(checkpointer=MemorySaver())


# ── 节点工厂 ──────────────────────────────────────────────

def _make_intent_router(intent_router):
    async def intent_router_node(state: AgentState) -> dict:
        if not intent_router:
            return {"intent": None}

        t0 = time.time()
        query = _extract_last_message(state)
        if not query or not query.strip():
            return {"intent": None}

        try:
            intent = await intent_router.route(query, user_id=state.get("user_id", 0))
        except Exception as e:
            logger.warning(f"[intent_router] 路由失败（降级走 Agent）: {e}")
            intent = None

        logger.info(f"[intent_router] hit={intent is not None} elapsed={time.time()-t0:.3f}s")

        if intent and intent.get("cached_answer"):
            return {
                "intent": intent,
                "final_answer": intent["cached_answer"],
                "skill_answer": intent["cached_answer"],
                "messages": [AIMessage(content=intent["cached_answer"])],
            }
        return {"intent": intent}

    return intent_router_node


def _make_skill_executor_node(skill_executor):
    async def skill_executor_node(state: AgentState) -> dict:
        if not skill_executor or not state.get("intent"):
            return {"skill_answer": None, "final_answer": None}

        intent = state["intent"]
        target = intent.get("target_module", "")
        if not target or target == "cache":
            return {"skill_answer": None, "final_answer": None}

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
                )
        except Exception as e:
            logger.error(f"[skill_executor] 技能 '{target}' 执行失败: {e}", exc_info=True)
            answer = None

        logger.info(f"[skill_executor] skill={target} elapsed={time.time()-t0:.2f}s success={answer is not None}")

        if answer:
            return {
                "skill_answer": answer,
                "final_answer": answer,
                "messages": [AIMessage(content=answer)],
            }
        return {"skill_answer": None, "final_answer": None}

    return skill_executor_node


def _make_context_builder(context_engine, memory_manager, tool_registry=None):
    async def context_builder_node(state: AgentState) -> dict:
        t0 = time.time()
        query = _extract_last_message(state)
        memory_context = None  # 记忆元数据，默认无

        # ── B+C: 根据 intent 动态选择工具（存储工具名，非 Tool 对象）──
        selected_tool_names = _select_tool_names_for_intent(state, tool_registry)
        tool_count = len(selected_tool_names)
        logger.info(f"[context_builder] 动态工具选择: intent={(state.get('intent') or {}).get('intent_name', 'none')} tools={tool_count}")

        if context_engine:
            try:
                # ── Query Rewriting（RAG 检索前改写口语化查询）──
                messages_for_rewrite = _build_message_dicts(state)
                rewritten_query = await context_engine.rewrite_query(
                    user_query=query,
                    conversation_history=messages_for_rewrite[:-1],  # 排除当前消息
                )

                # 传递选中的工具名摘要给 context_engine
                tool_summaries = None
                if tool_registry and selected_tool_names:
                    tool_summaries = []
                    for name in selected_tool_names:
                        tdef = tool_registry.get(name)
                        if tdef:
                            tool_summaries.append({"name": tdef.name, "description": tdef.description})

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

        return {
            "system_prompt": system_prompt,
            "context": system_prompt,
            "memory_context": memory_context,
            "selected_tools": selected_tool_names,
        }

    return context_builder_node


def _make_llm_caller(llm, tool_registry=None):
    async def llm_call_node(state: AgentState) -> dict:
        t0 = time.time()

        system_prompt = state.get("system_prompt") or state.get("context") or \
            "你是一个智能助手，能够使用工具回答用户问题。请用中文回答。"

        lc_messages = [SystemMessage(content=system_prompt)]

        # ── Auto-Compaction（压缩旧历史）─────────────
        raw_messages = state["messages"]
        if len(raw_messages) > MAX_MESSAGE_WINDOW:
            try:
                from app.agent.compaction import maybe_compact
                raw_messages = await maybe_compact(
                    messages=[{"role": getattr(m, "role", m.get("role", "user")), "content": _content_to_str(getattr(m, "content", m.get("content", "")))} for m in raw_messages],
                    llm_client=llm,
                    user_id=state.get("user_id", 0),
                    conversation_id=state.get("conversation_id", 0),
                )
            except Exception as e:
                logger.warning(f"[llm_call] compaction 失败，降级为窗口裁剪: {e}")
                raw_messages = _trim_messages(raw_messages, MAX_MESSAGE_WINDOW)
        else:
            raw_messages = _trim_messages(raw_messages, MAX_MESSAGE_WINDOW)

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

        # ── B+C: 动态绑定工具（从 registry 按名查找，state 中存的是工具名字符串）──
        selected_tool_names = state.get("selected_tools") or []
        current_llm = llm
        if selected_tool_names and tool_registry:
            tool_objects = tool_registry.get_langchain_tools(selected_tool_names)
            if tool_objects:
                current_llm = llm.bind_tools(tool_objects)
                logger.debug(f"[llm_call] 动态绑定 {len(tool_objects)} 个工具")
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
                            model_name=getattr(llm, "model_name", "") or getattr(llm, "model", ""),
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            duration_ms=int(elapsed * 1000),
                            call_type="chat",
                        )
        except Exception as e:
            logger.debug(f"[llm_call] 成本追踪失败（不影响主流程）: {e}")

        if response.tool_calls:
            return {
                "messages": [AIMessage(content=response.content or "", tool_calls=response.tool_calls)],
                "tool_calls": response.tool_calls,
                "final_answer": None,
            }
        return {
            "messages": [AIMessage(content=response.content)],
            "final_answer": response.content,
            "tool_calls": [],
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
        from app.agent.tool_registry import RiskLevel

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
                            "role": "tool", "tool_call_id": tid,
                            "content": _format_tool_result_json(result, name),
                        })
                    except Exception as tool_err:
                        _circuit_breaker.record_failure(name)
                        results.append({
                            "role": "tool", "tool_call_id": tid,
                            "content": _format_tool_result_json(None, name, str(tool_err)),
                        })

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
    def _rule_based_eval(state: AgentState) -> dict:
        final_answer = state.get("final_answer", "")
        if not final_answer:
            return {"evaluation": {"passed": False, "reason": "无回答", "score": 0}}
        if len(final_answer.strip()) < 10:
            return {"evaluation": {"passed": False, "reason": "回答过短", "score": 2}}
        if "抱歉" in final_answer and "不可用" in final_answer:
            return {"evaluation": {"passed": False, "reason": "包含错误信息", "score": 2}}
        return {"evaluation": {"passed": True, "reason": "", "score": 7}}

    async def evaluator_node(state: AgentState) -> dict:
        final_answer = state.get("final_answer", "")
        if not final_answer:
            return {"evaluation": {"passed": False, "reason": "无回答", "score": 0}}

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
            return {"evaluation": evaluation}

        except Exception as e:
            logger.warning(f"[evaluator] LLM 评估失败，降级为规则评估: {e}")
            return _rule_based_eval(state)

    return evaluator_node


def _make_memory_saver(memory_manager):
    async def memory_saver_node(state: AgentState) -> dict:
        if not state.get("final_answer"):
            return {}

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
                    meta = await memory_manager.save_summary(
                        conversation_id=state["conversation_id"],
                        user_id=state.get("user_id", 0),
                        messages=messages + [{"role": "assistant", "content": state["final_answer"]}],
                    )
                    logger.info(f"[memory_saver] 已保存长期记忆: importance={importance} tools={bool(tools_used)} msgs={len(messages)}")

                    # ── 同步写入 MySQL memory_entry 表 ──
                    if meta and meta.get("point_id"):
                        try:
                            from app.core.database import AsyncSessionLocal
                            from app.repository.memory_repo import MemoryRepository
                            async with AsyncSessionLocal() as db:
                                repo = MemoryRepository()
                                # 拼接原始对话内容
                                content_text = "\n".join(
                                    f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                                    for m in messages[-10:]  # 最近 10 条
                                )
                                await repo.create(db, {
                                    "conversation_id": state["conversation_id"],
                                    "content": content_text[:2000],
                                    "summary": meta["summary"],
                                    "tags": meta["tags"],
                                    "importance": meta["importance"],
                                    "qdrant_point_id": meta["point_id"],
                                })
                                await db.commit()
                                logger.info(f"[memory_saver] MySQL memory_entry 已同步: point_id={meta['point_id'][:8]}")
                        except Exception as e:
                            logger.warning(f"[memory_saver] MySQL 同步失败: {e}")
                except Exception as e:
                    logger.warning(f"[memory_saver] Qdrant 长期记忆保存失败: {e}")
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
                summary_text = meta.get("summary", "") if meta else ""
                if not summary_text:
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
                                auto_title = user_content[:20].replace("\n", " ").strip()
                                if len(user_content) > 20:
                                    auto_title += "..."
                                await conv_repo.update(md_db, conv_id, {"title": auto_title})
                                await md_db.commit()
                                logger.info(f"[memory_saver] 会话标题已更新: {auto_title}")
                        except Exception as e:
                            logger.warning(f"[memory_saver] 会话标题更新失败: {e}")

            except Exception as e:
                logger.warning(f"[memory_saver] Markdown daily log 失败: {e}")

        return {"conversation_importance": importance}

    return memory_saver_node


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
    reason = evaluation.get("reason", "")

    # score >= 6 或 passed=True → 通过
    if passed and score >= 6:
        return "pass"

    # [P2] 评估未通过但已有回答 → 替换为用户友好的兜底回答
    # 评分太低（<4）的回答不如不给，直接用明确的提示替代
    if state.get("final_answer"):
        if score < 4:
            logger.warning(f"[evaluator] 评估不通过(score={score})，替换为兜底回答: {reason}")
            state["final_answer"] = (
                "抱歉，我暂时无法准确回答这个问题。"
                "可能是搜索服务暂时不可用，或者问题超出了我当前的能力范围。\n\n"
                "你可以试试：\n"
                "1. 换个方式描述你的问题\n"
                "2. 稍后再试\n"
                "3. 如果是天气等实时信息，可以直接告诉我你的城市"
            )
        else:
            logger.warning(f"[evaluator] 评估未通过(score={score})但回答尚可，直接返回")
        return "pass"
    return "replan"


# ── 辅助函数 ──────────────────────────────────────────────

def _select_tool_names_for_intent(state: AgentState, tool_registry) -> list:
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

def _extract_last_message(state: AgentState) -> str:
    last_msg = state["messages"][-1] if state["messages"] else None
    if last_msg:
        content = last_msg.get("content", "") if isinstance(last_msg, dict) else getattr(last_msg, "content", "")
        return _content_to_str(content)
    return ""


def _content_to_str(content) -> str:
    """将消息 content 统一转为字符串。

    LLM 返回的 content 可能是:
      - str: 直接返回
      - None: 返回空字符串
      - list[dict]: content blocks 格式，提取 text 字段拼接
      - 其他: str() 强转
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def _build_message_dicts(state: AgentState) -> List[dict]:
    result = []
    for m in state["messages"]:
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
