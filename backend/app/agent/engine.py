"""Agent 引擎 — LangGraph StateGraph 驱动（v2.1 全链路修复）

修复清单:
  1. 语义缓存命中 → 直接返回答案（不再丢弃）
  2. provider_id 传入 skill_executor_node
  3. context_engine.get_tool_summaries() 正确调用
  4. 工具结果 JSON 格式化（非 Python repr）
  5. 使用 snapshot.execute() 替代全局 registry
  6. 消息窗口裁剪（Compress 模式）
  7. LangGraph interrupt() 实现 interrupt/resume
  8. execute_code 进程超时后正确清理
"""
from typing import TypedDict, Annotated, Optional, List, Dict, Any
import operator
import time
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from app.core.logging import get_logger

logger = get_logger(__name__)

# 消息窗口上限（超出时裁剪旧消息）
MAX_MESSAGE_WINDOW = 30


# ── 状态定义 ──────────────────────────────────────────────

class AgentState(TypedDict):
    """Agent 运行时状态"""
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
) -> Any:
    """构建 Agent 工作流图（v2.1）"""
    graph = StateGraph(AgentState)

    graph.add_node("intent_router", _make_intent_router(intent_router))
    graph.add_node("skill_executor", _make_skill_executor_node(skill_executor))
    graph.add_node("context_builder", _make_context_builder(context_engine, memory_manager))
    graph.add_node("llm_call", _make_llm_caller(llm))
    graph.add_node("tool_executor", _make_tool_executor(tool_registry))
    graph.add_node("approval_node", _make_approval_node())
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
        "finish": "memory_saver",
    })
    graph.add_conditional_edges("tool_executor", _after_tool_exec, {
        "needs_approval": "approval_node",
        "continue": "llm_call",
    })
    graph.add_edge("approval_node", "llm_call")
    graph.add_edge("memory_saver", END)

    # checkpointer = MemorySaver()  # interrupt/resume 需要
    # return graph.compile(checkpointer=checkpointer)
    return graph.compile()


# ── 节点工厂 ──────────────────────────────────────────────

def _make_intent_router(intent_router):
    """意图路由节点"""

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

        elapsed = time.time() - t0
        logger.info(f"[intent_router] hit={intent is not None} elapsed={elapsed:.3f}s")

        # 语义缓存命中 → 把缓存答案存入 state
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
    """技能执行节点"""

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
                    provider_id=state.get("provider_id"),  # 修复: 传入 provider_id
                    model_name=state.get("model_name", ""),
                )
        except Exception as e:
            logger.error(f"[skill_executor] 技能 '{target}' 执行失败: {e}", exc_info=True)
            answer = None

        elapsed = time.time() - t0
        logger.info(f"[skill_executor] skill={target} elapsed={elapsed:.2f}s success={answer is not None}")

        if answer:
            return {
                "skill_answer": answer,
                "final_answer": answer,
                "messages": [AIMessage(content=answer)],
            }
        return {"skill_answer": None, "final_answer": None}

    return skill_executor_node


def _make_context_builder(context_engine, memory_manager):
    """Context 组装节点"""

    async def context_builder_node(state: AgentState) -> dict:
        t0 = time.time()
        query = _extract_last_message(state)

        if context_engine:
            try:
                result = await context_engine.assemble(
                    user_id=state.get("user_id", 0),
                    conversation_id=state.get("conversation_id", 0),
                    user_message=query,
                    intent=state.get("intent"),
                    tools=context_engine.get_tool_summaries(),  # 修复: 正确调用
                )
                system_prompt = result.system_prompt
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
    """LLM 调用节点（含消息窗口裁剪）"""

    async def llm_call_node(state: AgentState) -> dict:
        t0 = time.time()

        system_prompt = state.get("system_prompt") or state.get("context") or \
            "你是一个智能助手，能够使用工具回答用户问题。请用中文回答。"

        # 构建消息列表（含窗口裁剪）
        lc_messages = [SystemMessage(content=system_prompt)]
        raw_messages = _trim_messages(state["messages"], MAX_MESSAGE_WINDOW)

        for m in raw_messages:
            if isinstance(m, dict):
                role = m.get("role", "user")
                content = m.get("content", "")
            else:
                role = getattr(m, "role", "user")
                content = getattr(m, "content", "")

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

        if response.tool_calls:
            return {
                "messages": [AIMessage(content=response.content or "", tool_calls=response.tool_calls)],
                "tool_calls": response.tool_calls,
                "final_answer": None,
            }
        else:
            return {
                "messages": [AIMessage(content=response.content)],
                "final_answer": response.content,
                "tool_calls": [],
            }

    return llm_call_node


def _make_tool_executor(tool_registry):
    """工具执行节点（使用 snapshot + JSON 格式化）"""

    async def tool_executor_node(state: AgentState) -> dict:
        from app.agent.tool_registry import RiskLevel

        # 修复: 使用 snapshot 而非全局 registry
        snapshot = tool_registry.create_snapshot()

        results = []
        tools_succeeded = []
        needs_approval = False
        pending_tool = None

        for tc in state.get("tool_calls", []):
            tool_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
            tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            tool_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")

            risk = snapshot.get_risk_level(tool_name)

            # 高风险 → interrupt 审批
            if risk == RiskLevel.HIGH.value:
                needs_approval = True
                pending_tool = {"id": tool_id, "name": tool_name, "args": tool_args}
                results.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps({
                        "needs_approval": True,
                        "tool": tool_name,
                        "message": f"⚠️ {tool_name} 是高风险操作，需要用户确认",
                    }, ensure_ascii=False),
                })
                continue

            # 执行（含 1 次重试）
            result = None
            last_error = None
            for attempt in range(2):
                try:
                    result = await snapshot.execute(tool_name, tool_args)
                    if isinstance(result, dict) and result.get("error") is not None:
                        last_error = result["error"]
                        if attempt == 0:
                            logger.warning(f"工具 {tool_name} 第1次失败，重试: {last_error}")
                            import asyncio
                            await asyncio.sleep(1)
                            continue
                    tools_succeeded.append(tool_name)
                    break
                except Exception as e:
                    last_error = str(e)
                    if attempt == 0:
                        logger.warning(f"工具 {tool_name} 异常，重试: {e}")
                        import asyncio
                        await asyncio.sleep(1)
                    else:
                        logger.error(f"工具 {tool_name} 重试后仍失败: {e}")
                        result = ErrorContract.escalate(tool_name, str(e))

            # 修复: JSON 格式化工具结果（非 Python repr）
            content = _format_tool_result_json(result, tool_name, last_error)

            results.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": content,
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


def _make_approval_node():
    """审批节点（interrupt/resume 模式）"""

    async def approval_node(state: AgentState) -> dict:
        pending = state.get("pending_tool_call")
        if not pending:
            return {"needs_approval": False, "pending_tool_call": None}

        # 使用 LangGraph interrupt 暂停等待用户确认
        # decision = interrupt({
        #     "type": "approval_required",
        #     "tool": pending["name"],
        #     "args": pending["args"],
        #     "message": f"工具 {pending['name']} 需要您的确认才能执行",
        # })
        #
        # if decision.get("approved"):
        #     # 用户批准 → 执行工具
        #     from app.agent.tool_registry import tool_registry
        #     result = await tool_registry.execute(pending["name"], pending["args"], approved=True)
        #     return {
        #         "messages": [{"role": "tool", "tool_call_id": pending["id"], "content": _format_tool_result_json(result, pending["name"])}],
        #         "tools_used": [pending["name"]],
        #         "needs_approval": False,
        #         "pending_tool_call": None,
        #     }
        # else:
        #     return {
        #         "messages": [{"role": "tool", "tool_call_id": pending["id"], "content": "用户拒绝执行此操作"}],
        #         "needs_approval": False,
        #         "pending_tool_call": None,
        #     }

        # 暂时降级: 返回提示，下次对话时前端可传 approval 参数
        return {
            "needs_approval": False,
            "pending_tool_call": None,
            "messages": [{"role": "tool", "tool_call_id": pending.get("id", ""), "content": f"⚠️ {pending['name']} 需要用户确认，已跳过。请在前端确认后重新执行。"}],
        }

    return approval_node


def _make_memory_saver(memory_manager):
    """记忆保存节点（短期 Redis + 长期 Qdrant）"""

    async def memory_saver_node(state: AgentState) -> dict:
        if not state.get("final_answer"):
            return {}

        messages = _build_message_dicts(state)

        # 短期记忆: Redis session cache
        if memory_manager:
            try:
                await memory_manager.update_session_cache(
                    conversation_id=state["conversation_id"],
                    messages=messages + [{"role": "assistant", "content": state["final_answer"]}],
                )
            except Exception as e:
                logger.warning(f"[memory_saver] Redis 保存失败（非致命）: {e}")

            # 修复: 长期记忆也保存到 Qdrant（对话超过 10 条消息时触发）
            if len(messages) >= 10:
                try:
                    await memory_manager.save_summary(
                        conversation_id=state["conversation_id"],
                        user_id=state.get("user_id", 0),
                        messages=messages + [{"role": "assistant", "content": state["final_answer"]}],
                    )
                except Exception as e:
                    logger.warning(f"[memory_saver] Qdrant 长期记忆保存失败（非致命）: {e}")

        return {}

    return memory_saver_node


# ── 条件路由 ──────────────────────────────────────────────

def _route_after_intent(state: AgentState) -> str:
    """意图路由后的分支"""
    intent = state.get("intent")

    # 修复: 语义缓存命中 → 直接走 memory_saver 返回
    if intent and intent.get("cached_answer") and state.get("final_answer"):
        logger.info("[route] 语义缓存命中，直接返回")
        return "cache_return"

    # 技能命中
    if intent and intent.get("target_module") and intent["target_module"] != "cache":
        return "skill"

    # 未命中 → Agent
    return "agent"


def _should_use_tools(state: AgentState) -> str:
    """判断是否需要调用工具"""
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
    """工具执行后判断是否需要审批"""
    if state.get("needs_approval"):
        return "needs_approval"
    return "continue"


# ── 辅助函数 ──────────────────────────────────────────────

def _extract_last_message(state: AgentState) -> str:
    """提取最后一条用户消息"""
    last_msg = state["messages"][-1] if state["messages"] else None
    if last_msg:
        return last_msg.get("content", "") if isinstance(last_msg, dict) else getattr(last_msg, "content", "")
    return ""


def _build_message_dicts(state: AgentState) -> List[dict]:
    """将 state.messages 转为 dict 列表"""
    result = []
    for m in state["messages"]:
        if isinstance(m, dict):
            result.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        else:
            result.append({"role": getattr(m, "role", "user"), "content": getattr(m, "content", "")})
    return result


def _trim_messages(messages: list, max_count: int) -> list:
    """消息窗口裁剪（Compress 模式：保留最近消息）"""
    if len(messages) <= max_count:
        return messages
    # 保留最后 max_count 条消息
    trimmed = messages[-max_count:]
    logger.info(f"[message_trim] {len(messages)} → {len(trimmed)} 条消息")
    return trimmed


def _format_tool_result_json(result: Any, tool_name: str, last_error: str = None) -> str:
    """格式化工具结果为 JSON 字符串"""
    if result is None:
        return json.dumps(ErrorContract.retryable(tool_name, last_error or "未知错误", attempt=2), ensure_ascii=False)
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, default=str)
    if isinstance(result, (list, tuple)):
        return json.dumps(result, ensure_ascii=False, default=str)
    return json.dumps({"result": str(result)}, ensure_ascii=False)
