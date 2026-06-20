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
import os

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledGraph
from langgraph.checkpoint.memory import MemorySaver

from app.core.logging import get_logger
from app.agent.state import AgentState, InputState, OutputState, Context

# ── 从子模块导入 ──────────────────────────────────────────
from app.agent.utils.common import ErrorContract, CircuitBreaker, _circuit_breaker
from app.agent.utils.nodes import (
    _make_model_selector_node, _make_intent_router,
    _make_skill_executor_node, _make_context_builder,
    _make_llm_caller, _make_tool_executor,
    _make_approval_node, _make_evaluator_node, _make_memory_saver,
    _route_after_intent, _should_use_tools,
    _after_tool_exec, _after_approval, _after_eval, _after_memory,
    _after_goal_eval, _after_goal_replan,
    _select_tool_names_for_intent, _extract_last_message,
)
from app.agent.utils.goal_nodes import (
    _make_goal_evaluator, _make_goal_status_updater, _make_goal_replanner,
)

logger = get_logger(__name__)

DEFAULT_AGENT_TIMEOUT = 300


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
) -> CompiledGraph:
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
    goal_status_updater = _make_goal_status_updater(llm)
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
        "memory_saver": "memory_saver",
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

