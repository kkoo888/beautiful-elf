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
    构建 Agent 工作流图（v4.0）。

    Args:
        enable_interrupt: 是否启用 interrupt/resume（需要 checkpointer）
        timeout_seconds: 全局超时（秒），超时后 Agent 强制结束
    """
    graph = StateGraph(AgentState)

    graph.add_node("intent_router", _make_intent_router(intent_router))
    graph.add_node("skill_executor", _make_skill_executor_node(skill_executor))
    graph.add_node("context_builder", _make_context_builder(context_engine, memory_manager))
    graph.add_node("llm_call", _make_llm_caller(llm))
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
    return graph.compile()


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


def _make_context_builder(context_engine, memory_manager):
    async def context_builder_node(state: AgentState) -> dict:
        t0 = time.time()
        query = _extract_last_message(state)

        if context_engine:
            try:
                # ── Query Rewriting（RAG 检索前改写口语化查询）──
                messages_for_rewrite = _build_message_dicts(state)
                rewritten_query = await context_engine.rewrite_query(
                    user_query=query,
                    conversation_history=messages_for_rewrite[:-1],  # 排除当前消息
                )

                result = await context_engine.assemble(
                    user_id=state.get("user_id", 0),
                    conversation_id=state.get("conversation_id", 0),
                    user_message=rewritten_query,  # 用改写后的查询
                    intent=state.get("intent"),
                    tools=context_engine.get_tool_summaries(),
                )
                system_prompt = result.system_prompt

                # ── Context 压缩（超长时自动压缩）──
                if result.total_chars > MAX_CONTEXT_CHARS:
                    system_prompt = await context_engine.compress_context(
                        system_prompt, target_chars=MAX_CONTEXT_CHARS
                    )

                logger.info(f"[context_builder] sources={result.sources_used} chars={result.total_chars} elapsed={time.time()-t0:.2f}s")
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

        return {"system_prompt": system_prompt, "context": system_prompt}

    return context_builder_node


def _make_llm_caller(llm):
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
                    messages=[{"role": getattr(m, "role", m.get("role", "user")), "content": getattr(m, "content", m.get("content", ""))} for m in raw_messages],
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
                role, content = m.get("role", "user"), m.get("content", "")
            else:
                role, content = getattr(m, "role", "user"), getattr(m, "content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                tool_call_id = getattr(m, "tool_call_id", "") if not isinstance(m, dict) else m.get("tool_call_id", "")
                lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id or "unknown"))
            else:
                lc_messages.append(HumanMessage(content=content))

        try:
            response = await llm.ainvoke(lc_messages)
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

        # ── 2. 并行执行无依赖工具 ─────────────────────
        results = list(approval_results)
        tools_succeeded = []

        async def _execute_one(tool_name: str, tool_args: dict, tool_id: str) -> dict:
            """执行单个工具（含重试 + 熔断记录）"""
            result = None
            last_error = None
            for attempt in range(2):
                try:
                    result = await snapshot.execute(tool_name, tool_args)
                    if isinstance(result, dict) and result.get("error") is not None:
                        last_error = result["error"]
                        if attempt == 0:
                            logger.warning(f"工具 {tool_name} 第{attempt+1}次失败，重试: {last_error}")
                            await asyncio.sleep(1)
                            continue
                    _circuit_breaker.record_success(tool_name)
                    return {"tool_id": tool_id, "tool_name": tool_name, "result": result, "error": None}
                except Exception as e:
                    last_error = str(e)
                    if attempt == 0:
                        logger.warning(f"工具 {tool_name} 异常，重试: {e}")
                        await asyncio.sleep(1)
                    else:
                        _circuit_breaker.record_failure(tool_name)
                        result = ErrorContract.escalate(tool_name, str(e))

            return {"tool_id": tool_id, "tool_name": tool_name, "result": result, "error": last_error}

        # 并行执行所有可执行工具
        if executable_calls:
            exec_tasks = [
                _execute_one(tn, ta, ti) for _, tn, ta, ti in executable_calls
            ]
            exec_results = await asyncio.gather(*exec_tasks, return_exceptions=True)

            for r in exec_results:
                if isinstance(r, Exception):
                    logger.error(f"[tool_executor] 并行执行异常: {r}")
                    continue
                # 记录所有工具调用（成功+失败）
                tools_succeeded.append(r["tool_name"])
                # 集成 tracing 告警
                try:
                    from app.agent.tracing import check_tool_alert
                    check_tool_alert(r["tool_name"], r["error"] is None)
                except Exception:
                    pass
                content = _format_tool_result_json(r["result"], r["tool_name"], r["error"])
                results.append({"role": "tool", "tool_call_id": r["tool_id"], "content": content})

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

        eval_prompt = f"""你是一个严格的质量评估专家。请评估以下 AI 回答的质量。

【用户问题】
{user_query}

【AI 回答】
{final_answer[:2000]}

【使用的工具】
{', '.join(tools_used) if tools_used else '无'}

请从以下维度评估（1-10分）:
1. 准确性 — 回答是否正确、是否有事实错误
2. 完整性 — 是否完整回答了用户的问题
3. 幻觉检测 — 是否包含捏造的信息或数据
4. 工具使用 — 如果使用了工具，结果是否被正确引用

严格按以下 JSON 格式返回（不要输出其他内容）:
{{"score": 8, "passed": true, "reason": "简短说明", "dimensions": {{"accuracy": 8, "completeness": 7, "hallucination": 9, "tool_usage": 8}}}}

注意:
- score >= 6 为通过
- 如果回答包含明显的错误信息或"服务不可用"等，score <= 3
- 如果使用了工具但回答中没有引用工具结果，tool_usage <= 4"""

        try:
            response = await llm.ainvoke([HumanMessage(content=eval_prompt)])
            eval_text = response.content.strip()

            # 解析 JSON（容错处理）
            if eval_text.startswith("```"):
                eval_text = eval_text.split("```")[1]
                if eval_text.startswith("json"):
                    eval_text = eval_text[4:]

            evaluation = json.loads(eval_text)
            evaluation.setdefault("passed", evaluation.get("score", 0) >= 6)
            logger.info(f"[evaluator] LLM-as-Judge: score={evaluation.get('score')} passed={evaluation.get('passed')} reason={evaluation.get('reason', '')[:50]}")
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

        # 短期记忆: Redis
        if memory_manager:
            try:
                await memory_manager.update_session_cache(
                    conversation_id=state["conversation_id"],
                    messages=messages + [{"role": "assistant", "content": state["final_answer"]}],
                )
            except Exception as e:
                logger.warning(f"[memory_saver] Redis 保存失败: {e}")

            # 长期记忆: Qdrant（用重要性评分替代简单阈值）
            # 有工具调用 或 对话 >= 8 条 时触发评估
            tools_used = state.get("tools_used", [])
            if tools_used or len(messages) >= 8:
                try:
                    await memory_manager.save_summary(
                        conversation_id=state["conversation_id"],
                        user_id=state.get("user_id", 0),
                        messages=messages + [{"role": "assistant", "content": state["final_answer"]}],
                    )
                except Exception as e:
                    logger.warning(f"[memory_saver] Qdrant 长期记忆保存失败: {e}")

        return {}

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

    # score >= 6 或 passed=True → 通过
    if passed and score >= 6:
        return "pass"
    # 评估未通过但已有回答且迭代 >= 2 → 仍然返回（避免死循环）
    if state.get("final_answer") and state.get("iterations", 0) >= 2:
        logger.warning(f"[evaluator] 评估未通过(score={score})但已达迭代上限，强制返回")
        return "pass"
    return "replan"


# ── 辅助函数 ──────────────────────────────────────────────

def _extract_last_message(state: AgentState) -> str:
    last_msg = state["messages"][-1] if state["messages"] else None
    if last_msg:
        return last_msg.get("content", "") if isinstance(last_msg, dict) else getattr(last_msg, "content", "")
    return ""


def _build_message_dicts(state: AgentState) -> List[dict]:
    result = []
    for m in state["messages"]:
        if isinstance(m, dict):
            result.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        else:
            result.append({"role": getattr(m, "role", "user"), "content": getattr(m, "content", "")})
    return result


def _trim_messages(messages: list, max_count: int) -> list:
    if len(messages) <= max_count:
        return messages
    trimmed = messages[-max_count:]
    logger.info(f"[message_trim] {len(messages)} → {len(trimmed)} 条消息")
    return trimmed


def _format_tool_result_json(result: Any, tool_name: str, last_error: str = None) -> str:
    if result is None:
        return json.dumps(ErrorContract.retryable(tool_name, last_error or "未知错误", attempt=2), ensure_ascii=False)
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, default=str)
    if isinstance(result, (list, tuple)):
        return json.dumps(result, ensure_ascii=False, default=str)
    return json.dumps({"result": str(result)}, ensure_ascii=False)
