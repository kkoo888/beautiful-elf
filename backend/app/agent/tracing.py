"""统一可观测性 — LangSmith + 结构化日志（v3 重构）

架构:
  LangSmith（LangGraph 原生） → 全链路自动追踪（节点/工具/LLM）
  结构化日志 → JSON 格式，便于分析和告警
  自定义 span → 业务级追踪（意图路由、上下文组装、评估）

配置:
  环境变量（.env）:
    LANGCHAIN_TRACING_V2=true          # 启用 LangSmith
    LANGCHAIN_API_KEY=lsv2_xxx         # LangSmith API Key
    LANGCHAIN_PROJECT=beautiful-elf     # 项目名（LangSmith 控制台显示）
    LANGCHAIN_ENDPOINT=https://api.smith.langchain.com  # 可选

降级策略:
  未配置 LangSmith → 仅输出结构化日志（不影响功能）
"""
import os
import time
import json
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── LangSmith 状态 ────────────────────────────────────────

LANGSMITH_ENABLED = (
    os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    and os.getenv("LANGCHAIN_API_KEY") is not None
)

# 告警配置
ALERT_ERROR_RATE_THRESHOLD = 0.3
_alert_state: Dict[str, Dict] = {}


def init_tracing():
    """初始化可观测性（应用启动时调用）"""
    if LANGSMITH_ENABLED:
        # LangSmith 通过环境变量自动集成，无需手动初始化
        # LangGraph 的 astream_events / invoke 自动上报 trace
        logger.info(
            f"LangSmith 可观测性已启用 "
            f"(project={os.getenv('LANGCHAIN_PROJECT', 'default')}, "
            f"endpoint={os.getenv('LANGCHAIN_ENDPOINT', 'https://api.smith.langchain.com')})"
        )
    else:
        logger.info(
            "LangSmith 未配置，可观测性降级为结构化日志模式。"
            "设置 LANGCHAIN_TRACING_V2=true + LANGCHAIN_API_KEY 启用全链路追踪。"
        )


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
    # 成本追踪
    prompt_tokens: int = 0
    completion_tokens: int = 0


# ── 追踪上下文管理器 ──────────────────────────────────────

@contextmanager
def trace_span(name: str, metadata: Dict[str, Any] = None):
    """追踪 span（同步版）"""
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
    """追踪 span（异步版）"""
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
    """输出节点追踪日志（结构化 JSON）"""
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


# ── Agent 级追踪 ──────────────────────────────────────────

def trace_agent_run(trace_data: AgentTrace):
    """
    记录完整 Agent 调用。

    LangSmith 已自动追踪 LangGraph 的节点执行，
    这里补充业务级元数据（intent、成本、对话 ID）。
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
        "prompt_tokens": trace_data.prompt_tokens,
        "completion_tokens": trace_data.completion_tokens,
        "success": trace_data.error is None,
    }
    if trace_data.error:
        log_data["error"] = trace_data.error

    logger.info(f"[AgentTrace] {json.dumps(log_data, ensure_ascii=False)}")

    # LangSmith 已通过 LangGraph 原生集成自动上报
    # 这里补充业务级 metadata（如果需要在 LangSmith 中显示）
    if LANGSMITH_ENABLED:
        try:
            from langsmith import traceable
            # LangSmith trace 由 LangGraph 自动创建，
            # 此处仅记录额外的业务 metadata 到日志
            logger.debug(f"[LangSmith] agent_run metadata recorded for conv={trace_data.conversation_id}")
        except ImportError:
            pass


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


# ── 节点级追踪装饰器 ──────────────────────────────────────

def trace_node(name: str):
    """装饰器：自动追踪函数执行（同步 + 异步兼容）"""
    def decorator(func):
        if asyncio_iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with trace_async_span(name):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with trace_span(name):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator


def asyncio_iscoroutinefunction(func):
    """检查是否为异步函数"""
    import asyncio
    return asyncio.iscoroutinefunction(func)


# ── 工具告警 ──────────────────────────────────────────────

def check_tool_alert(tool_name: str, success: bool):
    """工具告警检查：失败率 > 30% 时触发告警"""
    if tool_name not in _alert_state:
        _alert_state[tool_name] = {"calls": 0, "failures": 0}

    state = _alert_state[tool_name]
    state["calls"] += 1
    if not success:
        state["failures"] += 1

    if state["calls"] >= 10:
        error_rate = state["failures"] / state["calls"]
        if error_rate > ALERT_ERROR_RATE_THRESHOLD:
            logger.warning(
                f"[ALERT] 工具 {tool_name} 失败率 {error_rate:.1%} "
                f"超过阈值 {ALERT_ERROR_RATE_THRESHOLD:.0%} "
                f"({state['failures']}/{state['calls']})"
            )
        _alert_state[tool_name] = {"calls": 0, "failures": 0}
