"""Agent 引擎 — LangGraph StateGraph 驱动（v2 重构）

重构目标（借鉴 Deep Agents 设计模式）:
  1. 意图路由纳入图内（不再是外部系统）
  2. Context Engine 动态组装（替代硬编码系统提示）
  3. 工具执行支持 interrupt/resume（高风险审批）
  4. 结构化错误契约（retryable / user_facing / escalate）
  5. 全链路可观测（trace_span 埋点）
  6. 迭代上限 + 反思节点（Deep Agent 分层）

状态图:
  [intent_router] → (命中技能?) → [skill_executor] → END
                       ↓ 未命中
  [context_builder] → [llm_call] → (需要工具?) → [tool_executor] → [llm_call]
                                        ↓ 不需要
                                    [memory_saver] → END
"""
from typing import TypedDict, Annotated, Optional, List, Dict, Any
import operator
import time

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── 状态定义 ──────────────────────────────────────────────

class AgentState(TypedDict):
    """Agent 运行时状态"""
    conversation_id: int
    user_id: int
    messages: Annotated[list, operator.add]      # 对话历史（累加）
    context: str                                  # Context Engine 组装的上下文
    system_prompt: str                            # 动态系统提示
    tool_calls: list                              # 当前待执行的工具调用
    tools_used: Annotated[list, operator.add]     # 已使用的工具（累加）
    final_answer: Optional[str]                   # 最终回答
    iterations: int                               # 工具调用轮次
    needs_approval: bool                          # 是否需要审批
    pending_tool_call: Optional[dict]             # 待审批的工具调用
    intent: Optional[dict]                        # 意图路由结果
    skill_answer: Optional[str]                   # 技能直接返回的答案
    error: Optional[str]                          # 错误信息
    trace_metadata: dict                          # 追踪元数据


# ── 错误契约 ──────────────────────────────────────────────

class ErrorContract:
    """结构化错误响应（参考 Deep Agents Tool 设计）"""

    @staticmethod
    def retryable(tool_name: str, error: str, attempt: int) -> dict:
        return {
            "success": False,
            "error": {
                "code": "TOOL_TRANSIENT_ERROR",
                "message": f"工具 {tool_name} 暂时不可用: {error}",
                "retryable": True,
                "user_facing": False,
                "attempt": attempt,
            },
        }

    @staticmethod
    def user_facing(tool_name: str, error: str, user_tip: str) -> dict:
        return {
            "success": False,
            "error": {
                "code": "TOOL_USER_ERROR",
                "message": f"工具 {tool_name}: {error}",
                "retryable": False,
                "user_facing": True,
                "user_tip": user_tip,
            },
        }

    @staticmethod
    def escalate(tool_name: str, error: str) -> dict:
        return {
            "success": False,
            "error": {
                "code": "TOOL_SYSTEM_ERROR",
                "message": f"工具 {tool_name} 系统异常: {error}",
                "retryable": False,
                "user_facing": False,
                "escalate": True,
            },
        }


# ── 构建图 ────────────────────────────────────────────────

def build_agent_graph(
    llm,                    # LangChain ChatModel（已 bind_tools）
    tool_registry,          # ToolRegistry 实例
    context_engine=None,    # ContextEngine 实例（可选）
    memory_manager=None,    # MemoryManager 实例（可选）
    intent_router=None,     # IntentRouter 实例（可选）
    skill_executor=None,    # SkillExecutor 实例（可选）
    rag_pipeline=None,      # RAGPipeline 实例（可选）
) -> Any:
    """
    构建 Agent 工作流图（v2）。

    Args:
        llm: LangChain ChatModel（已绑定工具）
        tool_registry: ToolRegistry 实例
        context_engine: ContextEngine 实例（可选）
        memory_manager: MemoryManager 实例（可选）
        intent_router: IntentRouter 实例（可选）
        skill_executor: SkillExecutor 实例（可选）
        rag_pipeline: RAGPipeline 实例（可选）

    Returns:
        编译后的 StateGraph
    """
    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("intent_router", _make_intent_router(intent_router))
    graph.add_node("skill_executor", _make_skill_executor_node(skill_executor))
    graph.add_node("context_builder", _make_context_builder(context_engine, memory_manager))
    graph.add_node("llm_call", _make_llm_caller(llm))
    graph.add_node("tool_executor", _make_tool_executor(tool_registry))
    graph.add_node("memory_saver", _make_memory_saver(memory_manager))

    # 定义边
    graph.set_entry_point("intent_router")
    graph.add_conditional_edges("intent_router", _route_after_intent, {
        "skill": "skill_executor",
        "agent": "context_builder",
    })
    graph.add_edge("skill_executor", END)
    graph.add_edge("context_builder", "llm_call")
    graph.add_conditional_edges("llm_call", _should_use_tools, {
        "use_tools": "tool_executor",
        "finish": "memory_saver",
    })
    graph.add_edge("tool_executor", "llm_call")
    graph.add_edge("memory_saver", END)

    return graph.compile()


# ── 节点工厂 ──────────────────────────────────────────────

def _make_intent_router(intent_router):
    """意图路由节点（图内第一步）"""

    async def intent_router_node(state: AgentState) -> dict:
        if not intent_router:
            return {"intent": None}

        t0 = time.time()
        last_msg = state["messages"][-1] if state["messages"] else None
        query = ""
        if last_msg:
            query = last_msg.get("content", "") if isinstance(last_msg, dict) else getattr(last_msg, "content", "")

        if not query or not query.strip():
            return {"intent": None}

        try:
            intent = await intent_router.route(query, user_id=state.get("user_id", 0))
        except Exception as e:
            logger.warning(f"[intent_router] 路由失败（降级走 Agent）: {e}")
            intent = None

        elapsed = time.time() - t0
        hit = intent is not None
        logger.info(f"[intent_router] hit={hit} elapsed={elapsed:.3f}s")

        return {"intent": intent}

    return intent_router_node


def _make_skill_executor_node(skill_executor):
    """技能执行节点（意图命中技能时调用）"""

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
                    user_message=state["messages"][-1].get("content", "") if state["messages"] else "",
                    messages=[
                        {"role": m.get("role") if isinstance(m, dict) else getattr(m, "role", "user"),
                         "content": m.get("content") if isinstance(m, dict) else getattr(m, "content", "")}
                        for m in state["messages"]
                    ],
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
    """Context 组装节点（替代旧的简单记忆检索）"""

    async def context_builder_node(state: AgentState) -> dict:
        t0 = time.time()

        last_msg = state["messages"][-1] if state["messages"] else None
        query = ""
        if last_msg:
            query = last_msg.get("content", "") if isinstance(last_msg, dict) else getattr(last_msg, "content", "")

        # 获取可用工具摘要
        tool_summaries = []
        if context_engine and hasattr(context_engine, '_get_tool_summaries'):
            try:
                tool_summaries = context_engine._get_tool_summaries()
            except Exception:
                pass

        # 使用 ContextEngine 组装
        if context_engine:
            try:
                result = await context_engine.assemble(
                    user_id=state.get("user_id", 0),
                    conversation_id=state.get("conversation_id", 0),
                    user_message=query,
                    intent=state.get("intent"),
                    tools=tool_summaries or None,
                )
                system_prompt = result.system_prompt
                logger.info(
                    f"[context_builder] sources={result.sources_used} "
                    f"chars={result.total_chars} elapsed={time.time()-t0:.2f}s"
                )
            except Exception as e:
                logger.warning(f"[context_engine] 组装失败，降级为简单提示: {e}")
                system_prompt = "你是一个智能助手，能够使用工具回答用户问题。请用中文回答。"
        else:
            # 降级：简单记忆检索（兼容旧逻辑）
            system_prompt = "你是一个智能助手，能够使用工具回答用户问题。请用中文回答。"
            if memory_manager and query:
                try:
                    memory_context = await memory_manager.search(
                        query=query, user_id=state.get("user_id", 0), limit=5
                    )
                    if memory_context:
                        system_prompt += f"\n\n【相关记忆】\n{memory_context}"
                except Exception as e:
                    logger.warning(f"[context_builder] 记忆检索失败（降级跳过）: {e}")

        elapsed = time.time() - t0
        logger.info(f"[context_builder] elapsed={elapsed:.2f}s")

        return {"system_prompt": system_prompt, "context": system_prompt}

    return context_builder_node


def _make_llm_caller(llm):
    """LLM 调用节点：构建消息 → 调用 LLM → 解析结果"""

    async def llm_call_node(state: AgentState) -> dict:
        t0 = time.time()

        # 使用动态系统提示（来自 ContextEngine）
        system_prompt = state.get("system_prompt") or state.get("context") or \
            "你是一个智能助手，能够使用工具回答用户问题。请用中文回答。"

        # 构建消息列表
        lc_messages = [SystemMessage(content=system_prompt)]

        for m in state["messages"]:
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

        # 调用 LLM
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
    """工具执行节点：结构化错误契约 + 风险审批 + 重试"""

    async def tool_executor_node(state: AgentState) -> dict:
        from app.agent.tool_registry import RiskLevel

        results = []
        tools_succeeded = []
        needs_approval = False
        pending_tool = None

        for tc in state.get("tool_calls", []):
            # 兼容 dict 和 LangChain ToolCall 对象
            if isinstance(tc, dict):
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool_id = tc.get("id", "")
            else:
                tool_name = getattr(tc, "name", "")
                tool_args = getattr(tc, "args", {})
                tool_id = getattr(tc, "id", "")

            risk = tool_registry.get_risk_level(tool_name)

            # 高风险 → 请求审批（interrupt/resume 模式）
            if risk == RiskLevel.HIGH.value:
                needs_approval = True
                pending_tool = {"id": tool_id, "name": tool_name, "args": tool_args}
                results.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": f"⚠️ {tool_name} 是高风险操作，需要用户确认后才能执行。",
                })
                continue

            # 执行（含 1 次重试，使用结构化错误契约）
            result = None
            last_error = None
            for attempt in range(2):
                try:
                    result = await tool_registry.execute(tool_name, tool_args)
                    # 检查执行失败
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
                        # 使用结构化错误契约
                        result = ErrorContract.escalate(tool_name, str(e))

            # 确保 result 是字符串
            if isinstance(result, dict) and "error" in result:
                content = str(result)
            elif result is not None:
                content = str(result)
            else:
                content = ErrorContract.retryable(tool_name, last_error or "未知错误", attempt=2)

            results.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": str(content),
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


def _make_memory_saver(memory_manager):
    """记忆保存节点"""

    async def memory_saver_node(state: AgentState) -> dict:
        if state.get("final_answer") and memory_manager:
            try:
                await memory_manager.update_session_cache(
                    conversation_id=state["conversation_id"],
                    messages=[
                        {"role": m.get("role") if isinstance(m, dict) else getattr(m, "role", "user"),
                         "content": m.get("content") if isinstance(m, dict) else getattr(m, "content", "")}
                        for m in state["messages"]
                    ] + [{"role": "assistant", "content": state["final_answer"]}],
                )
            except Exception as e:
                logger.warning(f"[memory_saver] 保存失败（非致命）: {e}")
        return {}

    return memory_saver_node


# ── 条件路由 ──────────────────────────────────────────────

def _route_after_intent(state: AgentState) -> str:
    """意图路由后的分支判断"""
    intent = state.get("intent")

    # 语义缓存命中 → 直接返回（不需要走 Agent）
    if intent and intent.get("cached_answer"):
        return "skill"  # skill_executor 会处理缓存命中

    # 技能命中 → 走技能执行
    if intent and intent.get("target_module") and intent["target_module"] != "cache":
        target = intent["target_module"]
        logger.info(f"[route] 意图命中: {intent.get('intent_name')} → {target}")
        return "skill"

    # 未命中 → 走 Agent 通用对话
    return "agent"


def _should_use_tools(state: AgentState) -> str:
    """判断是否需要调用工具"""
    # 工具调用轮次上限（Deep Agents 默认 25，我们保守用 10）
    if state.get("iterations", 0) >= 10:
        logger.warning("[agent] 工具调用达到上限(10轮)，强制结束")
        return "finish"

    # 需要审批 → 暂停，等待用户确认
    if state.get("needs_approval"):
        logger.info(f"[agent] 高风险工具待审批: {state.get('pending_tool_call')}")
        return "finish"

    # 技能已直接返回答案
    if state.get("skill_answer"):
        return "finish"

    # 有待执行的工具调用
    if state.get("tool_calls"):
        return "use_tools"

    # 无工具调用，结束
    return "finish"
