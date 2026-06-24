"""统一可观测性 — LangSmith / LangFuse 双模支持（v3）

架构:
  模式 A: LangSmith（LangGraph 原生） → 全链路自动追踪，零代码集成
  模式 B: LangFuse（开源自部署）      → 手动埋点，数据完全自主
  降级:   结构化日志                  → JSON 格式，无需任何外部服务

配置（.env，二选一）:
  ── LangSmith（推荐开发/小团队）──
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=lsv2_pt_your_key
    LANGCHAIN_PROJECT=beautiful-elf

  ── LangFuse（推荐生产/自部署）──
    LANGFUSE_PUBLIC_KEY=pk_xxx
    LANGFUSE_SECRET_KEY=sk_xxx
    LANGFUSE_HOST=https://your-langfuse-instance.com  # 自部署地址

  两者都未配置 → 降级为结构化日志
"""
import os
import time
import json
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── 双模检测 ──────────────────────────────────────────────

LANGSMITH_ENABLED = (
    os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    and os.getenv("LANGCHAIN_API_KEY") is not None
)

# LangSmith Engine（自动问题检测）— 需要 LANGCHAIN_PROJECT 指定项目名
# Engine 在 LangSmith 后台自动分析 trace，检测问题并提 PR 修复建议
# 代码层面只需确保 project 名正确，Engine 在 LangSmith 平台侧启用
LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT", "beautiful-elf")

LANGFUSE_ENABLED = os.getenv("LANGFUSE_PUBLIC_KEY") is not None

_langfuse_client = None

# 告警配置
ALERT_ERROR_RATE_THRESHOLD = 0.3
_alert_state: Dict[str, Dict] = {}


def init_tracing():
    """初始化可观测性（应用启动时调用）"""
    global _langfuse_client

    if LANGSMITH_ENABLED:
        logger.info(
            f"✅ LangSmith 可观测性已启用 "
            f"(project={os.getenv('LANGCHAIN_PROJECT', 'default')})"
        )
        return

    if LANGFUSE_ENABLED:
        try:
            from langfuse import Langfuse
            _langfuse_client = Langfuse(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            )
            logger.info(f"✅ LangFuse 可观测性已启用 (host={os.getenv('LANGFUSE_HOST', 'cloud')})")
            return
        except ImportError:
            logger.warning("缺少 langfuse 包，降级为结构化日志")
        except Exception as e:
            logger.warning(f"LangFuse 初始化失败: {e}，降级为结构化日志")

    logger.info(
        "可观测性: 结构化日志模式。"
        "配置 LANGCHAIN_TRACING_V2+API_KEY(LangSmith) 或 LANGFUSE_PUBLIC_KEY+SECRET_KEY(LangFuse) 启用可视化。"
    )


# ── 追踪数据结构 ──────────────────────────────────────────

@dataclass
class NodeTrace:
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: int = 0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class AgentTrace:
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
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tier: str = ""
    route_class: str = ""


# ── 追踪上下文管理器 ──────────────────────────────────────

@contextmanager
def trace_span(name: str, metadata: Dict[str, Any] = None):
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
    """输出节点追踪日志 + LangFuse span"""
    log_data = {
        "trace_node": node.name,
        "duration_ms": node.duration_ms,
        "success": node.success,
    }
    if node.metadata:
        log_data["meta"] = node.metadata
    if node.error:
        log_data["error"] = node.error

    level = "info" if node.success else "warning"
    getattr(logger, level)(f"[trace] {json.dumps(log_data, ensure_ascii=False)}")

    # LangFuse span
    if _langfuse_client:
        try:
            _langfuse_client.span(
                name=node.name,
                metadata={
                    **node.metadata,
                    "duration_ms": node.duration_ms,
                    "success": node.success,
                    "error": node.error,
                },
            )
        except Exception as e:
            logger.debug(f"LangFuse span 失败: {e}")


# ── Agent 级追踪 ──────────────────────────────────────────

def trace_agent_run(trace_data: AgentTrace):
    """记录完整 Agent 调用（日志 + LangFuse）"""
    log_data = {
        "trace_type": "agent_run",
        "conversation_id": trace_data.conversation_id,
        "user_id": trace_data.user_id,
        "intent_hit": trace_data.intent_hit,
        "tools_used": trace_data.tools_used,
        "iterations": trace_data.iterations,
        "total_duration_ms": trace_data.total_duration_ms,
        "prompt_tokens": trace_data.prompt_tokens,
        "completion_tokens": trace_data.completion_tokens,
        "success": trace_data.error is None,
    }
    if trace_data.error:
        log_data["error"] = trace_data.error

    logger.info(f"[AgentTrace] {json.dumps(log_data, ensure_ascii=False)}")

    # LangFuse trace
    if _langfuse_client:
        try:
            trace = _langfuse_client.trace(
                name="agent_run",
                metadata=log_data,
                user_id=str(trace_data.conversation_id),
                input={"message": trace_data.user_message[:500]},
                output={"answer": trace_data.final_answer[:500]},
            )
            for node in trace_data.nodes:
                trace.span(
                    name=node.name,
                    metadata={
                        **node.metadata,
                        "duration_ms": node.duration_ms,
                        "success": node.success,
                    },
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
    """简化版追踪（兼容旧接口）"""
    trace_agent_run(AgentTrace(
        conversation_id=conversation_id,
        user_message=user_message[:200],
        final_answer=response[:200],
        tools_used=tools_used,
        iterations=iterations,
        total_duration_ms=duration_ms,
    ))


# ── 工具告警 ──────────────────────────────────────────────

def check_tool_alert(tool_name: str, success: bool):
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
