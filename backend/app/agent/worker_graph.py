"""Worker Subgraph — 独立执行子任务的轻量级 ReAct Agent

架构:
  build_worker_graph() → CompiledStateGraph
  spawn_agent() 调用 graph.ainvoke() 执行子任务

State:
  WorkerState — 独立于 AgentState，子图内部自包含
"""
import operator
from typing import Annotated, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.agent.state import _content_blocks_to_str

logger = get_logger(__name__)

# ── Worker State ──────────────────────────────────────────


class WorkerState(BaseModel):
    """Worker 子图状态 — 独立于主 AgentState"""
    model_config = {"from_attributes": True}

    messages: Annotated[list, operator.add] = Field(default_factory=list, description="消息历史")
    task: str = Field(default="", description="子任务描述")
    context: str = Field(default="", description="背景信息")
    iteration: int = Field(default=0, description="当前迭代轮次")
    max_iterations: int = Field(default=5, description="最大 LLM 调用轮次")
    final_answer: Optional[str] = Field(default=None, description="最终回答")
    force_end: bool = Field(default=False, description="强制结束标志")
    parent_trace_id: str = Field(default="", description="父 Agent trace ID（追踪用）")
    parent_system_prompt: str = Field(default="", description="父 Agent 的 system prompt 子集")
    parent_memory: str = Field(default="", description="父 Agent 的相关记忆")


# ── 节点 ──────────────────────────────────────────────────


def _make_worker_llm_caller(llm, system_prompt: str):
    """LLM 调用节点 — 绑定工具，ReAct 循环"""

    async def llm_call(state: WorkerState):
        messages = list(state.get("messages", []))
        iteration = state.get("iteration", 0)
        max_iter = state.get("max_iterations", 5)

        # 首轮：注入 system prompt + task + parent context
        if iteration == 0:
            if system_prompt:
                messages.insert(0, SystemMessage(content=system_prompt))
            task = state.get("task", "")
            context = state.get("context", "")
            parent_prompt = state.get("parent_system_prompt", "")
            parent_memory = state.get("parent_memory", "")
            user_content = f"## 任务\n{task}"
            if context:
                user_content += f"\n\n## 背景信息\n{context}"
            if parent_prompt:
                user_content += f"\n\n## 父 Agent 指令摘要\n{parent_prompt[:1000]}"
            if parent_memory:
                user_content += f"\n\n## 相关记忆\n{parent_memory[:500]}"
            messages.append(HumanMessage(content=user_content))

        # 超过最大迭代 → 强制结束
        if iteration >= max_iter:
            last_content = ""
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    last_content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    break
            return {
                "final_answer": last_content or "任务执行达到最大迭代次数",
                "force_end": True,
            }

        response = await llm.ainvoke(messages)
        return {"messages": [response], "iteration": iteration + 1}

    return llm_call


def _make_worker_evaluator():
    """评估节点 — 判断任务是否完成"""

    async def evaluate(state: WorkerState):
        messages = state.get("messages", [])
        if not messages:
            return {"final_answer": "无响应"}

        last_msg = messages[-1]
        content = _content_blocks_to_str(getattr(last_msg, "content", "")) if isinstance(last_msg, AIMessage) else ""

        # 有 tool_calls → 继续执行
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return {}

        # 无 tool_calls → 任务完成
        return {"final_answer": content or "任务完成"}

    return evaluate


def _route_after_llm(state: WorkerState):
    """LLM 调用后路由：force_end → 结束，有 tool_calls → 执行工具，否则 → 评估"""
    if state.get("force_end") or state.get("final_answer"):
        return "end"
    messages = state.get("messages", [])
    if not messages:
        return "end"
    last_msg = messages[-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tools"
    return "evaluate"


def _route_after_eval(state: WorkerState):
    """评估后路由：有 final_answer → 结束，否则 → 继续 LLM"""
    if state.get("final_answer"):
        return "end"
    return "continue"


# ── 图构建 ────────────────────────────────────────────────


def build_worker_graph(
    llm,
    tools: list,
    system_prompt: str = "",
    max_iterations: int = 5,
    depth: int = 0,
) -> "CompiledStateGraph":
    """构建 Worker 子图 — 独立执行单个子任务的 ReAct Agent

    Args:
        llm: LangChain LLM 实例（已绑定工具或可绑定）
        tools: LangChain StructuredTool 列表
        system_prompt: Worker 的系统提示词
        max_iterations: 最大 LLM 调用轮次（防无限循环）
        depth: 当前嵌套深度（0=顶层，最大 2）
    """
    from langgraph.graph.state import CompiledStateGraph

    # 绑定工具到 LLM
    bound_llm = llm.bind_tools(tools) if tools else llm

    # 创建 ToolNode
    tool_node = ToolNode(tools) if tools else None

    graph = StateGraph(WorkerState)

    # 注册节点
    graph.add_node("llm_call", _make_worker_llm_caller(bound_llm, system_prompt))
    if tool_node:
        graph.add_node("tools", tool_node)
    graph.add_node("evaluate", _make_worker_evaluator())

    # 入口
    graph.add_edge(START, "llm_call")

    # 路由
    if tool_node:
        graph.add_conditional_edges("llm_call", _route_after_llm, {
            "tools": "tools",
            "evaluate": "evaluate",
            "end": END,
        })
        graph.add_edge("tools", "llm_call")
    else:
        graph.add_conditional_edges("llm_call", _route_after_llm, {
            "evaluate": "evaluate",
            "end": END,
        })

    graph.add_conditional_edges("evaluate", _route_after_eval, {
        "end": END,
        "continue": "llm_call",
    })

    return graph.compile()


# ── Worker 工具集 ─────────────────────────────────────────

WORKER_TOOL_NAMES = [
    "web_search",
    "execute_code",
    "read_file",
    "query_database",
    "web_fetch",
    "memory_search",
    "list_files",
]
