"""Agent 引擎 — LangGraph StateGraph 驱动

精简版（Step 1）：
  - context_builder: 仅记忆检索（RAG 后续接入）
  - llm_call: 调用 LLM（支持 Tool Calling）
  - tool_executor: 执行工具 + 风险审批 + 重试
  - memory_saver: 保存会话缓存

状态图:
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
    context: str                                  # RAG + 记忆上下文
    tool_calls: list                              # 当前待执行的工具调用
    tools_used: Annotated[list, operator.add]     # 已使用的工具（累加）
    final_answer: Optional[str]                   # 最终回答
    iterations: int                               # 工具调用轮次
    needs_approval: bool                          # 是否需要审批
    pending_tool_call: Optional[dict]             # 待审批的工具调用


# ── 构建图 ────────────────────────────────────────────────

def build_agent_graph(
    llm,                    # LangChain ChatModel（已 bind_tools）
    tool_registry,          # ToolRegistry 实例
    memory_manager=None,    # MemoryManager 实例（可选）
    context_manager=None,   # ContextManager 实例（可选）
) -> Any:
    """
    构建 Agent 工作流图。

    Args:
        llm: LangChain ChatModel（已绑定工具）
        tool_registry: ToolRegistry 实例
        memory_manager: MemoryManager（可选，无记忆时跳过）
        context_manager: ContextManager（可选，无上下文管理时跳过）

    Returns:
        编译后的 StateGraph
    """
    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("context_builder", _make_context_builder(memory_manager))
    graph.add_node("llm_call", _make_llm_caller(llm, context_manager))
    graph.add_node("tool_executor", _make_tool_executor(tool_registry))
    graph.add_node("memory_saver", _make_memory_saver(memory_manager))

    # 定义边
    graph.set_entry_point("context_builder")
    graph.add_edge("context_builder", "llm_call")
    graph.add_conditional_edges("llm_call", _should_use_tools, {
        "use_tools": "tool_executor",
        "finish": "memory_saver",
    })
    graph.add_edge("tool_executor", "llm_call")
    graph.add_edge("memory_saver", END)

    return graph.compile()


# ── 节点工厂 ──────────────────────────────────────────────

def _make_context_builder(memory_manager):
    """上下文构建节点：检索记忆（RAG 后续接入）"""

    async def context_builder_node(state: AgentState) -> dict:
        t0 = time.time()
        context_parts = []

        query = state["messages"][-1].content if state["messages"] else ""

        # 记忆检索（可选）
        if memory_manager and query:
            try:
                memory_context = await memory_manager.search(
                    query=query, user_id=state.get("user_id", 0), limit=5
                )
                if memory_context:
                    context_parts.append(f"【相关记忆】\n{memory_context}")
            except Exception as e:
                logger.warning(f"[context_builder] 记忆检索失败（降级跳过）: {e}")

        elapsed = time.time() - t0
        context = "\n\n".join(context_parts)
        logger.info(f"[context_builder] elapsed={elapsed:.2f}s has_context={bool(context)}")

        return {"context": context}

    return context_builder_node


def _make_llm_caller(llm, context_manager):
    """LLM 调用节点：构建消息 → 调用 LLM → 解析结果"""

    async def llm_call_node(state: AgentState) -> dict:
        t0 = time.time()

        # 系统提示
        system_prompt = "你是一个智能助手，能够使用工具回答用户问题。请用中文回答。"
        if state.get("context"):
            system_prompt += f"\n\n{state['context']}"

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
                # ToolMessage 需要 tool_call_id
                tool_call_id = getattr(m, "tool_call_id", "") if not isinstance(m, dict) else m.get("tool_call_id", "")
                lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id or "unknown"))
            else:
                lc_messages.append(HumanMessage(content=content))

        # 裁剪上下文（可选）
        if context_manager:
            try:
                raw_messages = [{"role": getattr(m, "type", "user"), "content": m.content} for m in lc_messages]
                trimmed = await context_manager.trim_messages(raw_messages, system_prompt)
                lc_messages = []
                for m in trimmed:
                    role = m.get("role", "user")
                    content = m.get("content", "")
                    if role == "system":
                        lc_messages.append(SystemMessage(content=content))
                    elif role == "assistant":
                        lc_messages.append(AIMessage(content=content))
                    else:
                        lc_messages.append(HumanMessage(content=content))
            except Exception as e:
                logger.warning(f"[llm_call] 上下文裁剪失败（使用原始消息）: {e}")

        # 调用 LLM
        try:
            response = await llm.ainvoke(lc_messages)
        except Exception as e:
            logger.error(f"[llm_call] LLM 调用失败: {e}")
            return {
                "messages": [AIMessage(content=f"抱歉，AI 服务暂时不可用：{e}")],
                "final_answer": f"抱歉，AI 服务暂时不可用：{e}",
                "tool_calls": [],
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
    """工具执行节点：风险审批 + 参数校验 + 重试"""

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

            # 高风险 → 请求审批
            if risk == RiskLevel.HIGH.value:
                needs_approval = True
                pending_tool = {"id": tool_id, "name": tool_name, "args": tool_args}
                results.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": f"⚠️ {tool_name} 是高风险操作，需要用户确认后才能执行。",
                })
                continue

            # 执行（含 1 次重试）
            result = None
            for attempt in range(2):
                try:
                    result = await tool_registry.execute(tool_name, tool_args)
                    # 检查执行失败
                    if isinstance(result, dict) and result.get("error") is not None:
                        if attempt == 0:
                            logger.warning(f"工具 {tool_name} 第1次失败，重试: {result['error']}")
                            import asyncio
                            await asyncio.sleep(1)
                            continue
                    tools_succeeded.append(tool_name)
                    break
                except Exception as e:
                    if attempt == 0:
                        logger.warning(f"工具 {tool_name} 异常，重试: {e}")
                        import asyncio
                        await asyncio.sleep(1)
                    else:
                        logger.error(f"工具 {tool_name} 重试后仍失败: {e}")
                        result = {"error": str(e)}

            # 确保 result 是字符串
            content = str(result) if result is not None else "工具执行无返回"

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

def _should_use_tools(state: AgentState) -> str:
    """判断是否需要调用工具"""
    # 工具调用轮次上限
    if state.get("iterations", 0) >= 5:
        logger.warning("[agent] 工具调用达到上限(5轮)，强制结束")
        return "finish"

    # 需要审批 → 暂停，等待用户确认
    if state.get("needs_approval"):
        logger.info(f"[agent] 高风险工具待审批: {state.get('pending_tool_call')}")
        return "finish"

    # 有待执行的工具调用
    if state.get("tool_calls"):
        return "use_tools"

    # 无工具调用，结束
    return "finish"
