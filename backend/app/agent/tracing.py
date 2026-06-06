"""LangFuse 可观测性 — Agent tracing（v2 重构）

重构点:
  1. trace_agent_run: 完整 Agent 调用链路追踪
  2. trace_node: 节点级追踪（context_builder / llm_call / tool_executor）
  3. 结构化日志: JSON 格式，便于分析
  4. 性能指标: 各节点耗时、token 使用、工具调用统计

设计原则:
  - LangFuse 可选，未配置时降级为结构化日志
  - 不影响主流程性能
"""
import os
import time
import json
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

from app.core.logging import get_logger

logger = get_logger(__name__)

LANGFUSE_ENABLED = os.getenv("LANGFUSE_PUBLIC_KEY") is not None
_tracer = None

# 告警配置
ALERT_ERROR_RATE_THRESHOLD = 0.3  # 工具失败率 > 30% 触发告警
_alert_state: Dict[str, Dict] = {}  # 工具调用统计（用于告警判断）


def init_tracing():
    """初始化 LangFuse（应用启动时调用）"""
    global _tracer
    if not LANGFUSE_ENABLED:
        logger.info("LangFuse 未配置，可观测性降级为结构化日志模式")
        return

    try:
        from langfuse import Langfuse
        _tracer = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        logger.info("LangFuse 可观测性已启用")
    except ImportError:
        logger.warning("缺少 langfuse 包，可观测性降级为结构化日志模式")
    except Exception as e:
        logger.warning(f"LangFuse 初始化失败: {e}")


def get_tracer():
    """获取 LangFuse 客户端"""
    return _tracer


# ── 追踪数据结构 ──────────────────────────────────────────

@dataclass
class NodeTrace:
    """单个节点的追踪数据"""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: int = 0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class AgentTrace:
    """完整 Agent 调用的追踪数据"""
    conversation_id: int = 0
    user_id: int = 0
    user_message: str = ""
    final_answer: str = ""
    intent_hit: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)
    iterations: int = 0
    total_duration_ms: int = 0
    nodes: List[NodeTrace] = field(default_factory=list)
    context_sources: List[str] = field(default_factory=list)
    error: Optional[str] = None


# ── 追踪上下文管理器 ──────────────────────────────────────

@contextmanager
def trace_span(name: str, metadata: Dict[str, Any] = None):
    """
    追踪 span 上下文管理器（同步版）。

    用法:
        with trace_span("llm_call", {"model": "qwen3.5:7b"}):
            response = await llm.ainvoke(messages)
    """
    node = NodeTrace(name=name, start_time=time.time(), metadata=metadata or {})
    try:
        yield node
        node.success = True
    except Exception as e:
        node.success = False
        node.error = str(e)
        raise
    finally:
        node.end_time = time.time()
        node.duration_ms = int((node.end_time - node.start_time) * 1000)
        _log_node_trace(node)


@asynccontextmanager
async def trace_async_span(name: str, metadata: Dict[str, Any] = None):
    """
    追踪 span 上下文管理器（异步版）。

    用法:
        async with trace_async_span("context_build", {"user_id": 1}):
            context = await context_engine.assemble(...)
    """
    node = NodeTrace(name=name, start_time=time.time(), metadata=metadata or {})
    try:
        yield node
        node.success = True
    except Exception as e:
        node.success = False
        node.error = str(e)
        raise
    finally:
        node.end_time = time.time()
        node.duration_ms = int((node.end_time - node.start_time) * 1000)
        _log_node_trace(node)


def _log_node_trace(node: NodeTrace):
    """输出节点追踪日志"""
    log_data = {
        "trace_node": node.name,
        "duration_ms": node.duration_ms,
        "success": node.success,
    }
    if node.metadata:
        log_data["meta"] = node.metadata
    if node.error:
        log_data["error"] = node.error

    if node.success:
        logger.info(f"[trace] {json.dumps(log_data, ensure_ascii=False)}")
    else:
        logger.warning(f"[trace] {json.dumps(log_data, ensure_ascii=False)}")

    # LangFuse 集成
    if _tracer:
        try:
            _tracer.span(name=node.name, metadata={
                **node.metadata,
                "duration_ms": node.duration_ms,
                "success": node.success,
                "error": node.error,
            })
        except Exception as e:
            logger.debug(f"LangFuse span 失败: {e}")


# ── Agent 级追踪 ──────────────────────────────────────────

def trace_agent_run(trace_data: AgentTrace):
    """
    记录完整 Agent 调用。

    在 Agent 图执行完毕后调用，汇总所有节点的追踪数据。
    """
    log_data = {
        "trace_type": "agent_run",
        "conversation_id": trace_data.conversation_id,
        "user_id": trace_data.user_id,
        "intent_hit": trace_data.intent_hit,
        "tools_used": trace_data.tools_used,
        "iterations": trace_data.iterations,
        "total_duration_ms": trace_data.total_duration_ms,
        "context_sources": trace_data.context_sources,
        "node_count": len(trace_data.nodes),
        "success": trace_data.error is None,
    }
    if trace_data.error:
        log_data["error"] = trace_data.error

    logger.info(f"[AgentTrace] {json.dumps(log_data, ensure_ascii=False)}")

    # LangFuse 集成
    if _tracer:
        try:
            trace = _tracer.trace(
                name="agent_run",
                metadata=log_data,
                user_id=str(trace_data.conversation_id),
            )
            # 添加子 span
            for node in trace_data.nodes:
                trace.span(
                    name=node.name,
                    metadata={**node.metadata, "duration_ms": node.duration_ms, "success": node.success},
                )
        except Exception as e:
            logger.debug(f"LangFuse trace 失败: {e}")


def trace_agent_call(
    conversation_id: int,
    user_message: str,
    response: str,
    tools_used: list,
    iterations: int,
    duration_ms: int,
):
    """简化版 Agent 调用追踪（兼容旧接口）"""
    trace_agent_run(AgentTrace(
        conversation_id=conversation_id,
        user_message=user_message[:200],
        final_answer=response[:200],
        tools_used=tools_used,
        iterations=iterations,
        total_duration_ms=duration_ms,
    ))


def check_tool_alert(tool_name: str, success: bool):
    """
    工具告警检查：失败率 > 30% 时触发告警。

    每次工具调用后调用此函数。
    """
    if tool_name not in _alert_state:
        _alert_state[tool_name] = {"calls": 0, "failures": 0}

    state = _alert_state[tool_name]
    state["calls"] += 1
    if not success:
        state["failures"] += 1

    # 每 10 次调用检查一次
    if state["calls"] >= 10:
        error_rate = state["failures"] / state["calls"]
        if error_rate > ALERT_ERROR_RATE_THRESHOLD:
            logger.warning(
                f"[ALERT] 工具 {tool_name} 失败率 {error_rate:.1%} "
                f"超过阈值 {ALERT_ERROR_RATE_THRESHOLD:.0%} "
                f"({state['failures']}/{state['calls']})"
            )
        # 重置计数
        _alert_state[tool_name] = {"calls": 0, "failures": 0}
