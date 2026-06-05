"""LangFuse 可观测性 — Agent tracing

职责:
  - 初始化 LangFuse 客户端
  - 提供 trace_span 上下文管理器
  - 记录 Agent 调用链路（LLM 调用、工具调用、耗时）

设计原则:
  - LangFuse 可选，未配置时降级为 noop
  - 不影响主流程性能
"""
import os
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any

from app.core.logging import get_logger

logger = get_logger(__name__)

LANGFUSE_ENABLED = os.getenv("LANGFUSE_PUBLIC_KEY") is not None
_tracer = None


def init_tracing():
    """初始化 LangFuse（应用启动时调用）"""
    global _tracer
    if not LANGFUSE_ENABLED:
        logger.info("LangFuse 未配置，可观测性降级为日志模式")
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
        logger.warning("缺少 langfuse 包，可观测性降级为日志模式")
    except Exception as e:
        logger.warning(f"LangFuse 初始化失败: {e}")


def get_tracer():
    """获取 LangFuse 客户端"""
    return _tracer


@contextmanager
def trace_span(name: str, metadata: Dict[str, Any] = None):
    """
    追踪 span 上下文管理器。

    用法:
        with trace_span("llm_call", {"model": "qwen3.5:7b"}):
            response = await llm.ainvoke(messages)

    未配置 LangFuse 时降级为 noop。
    """
    if not _tracer:
        yield _NoopSpan()
        return

    try:
        span = _tracer.span(name=name, metadata=metadata or {})
        yield span
    except Exception as e:
        logger.debug(f"LangFuse span 创建失败: {e}")
        yield _NoopSpan()


class _NoopSpan:
    """空 span，LangFuse 未启用时使用"""

    def update(self, **kwargs):
        pass

    def end(self):
        pass


def trace_agent_call(
    conversation_id: int,
    user_message: str,
    response: str,
    tools_used: list,
    iterations: int,
    duration_ms: int,
):
    """
    记录 Agent 调用（简化版，直接写日志）。

    完整版应通过 LangFuse API 记录。
    """
    logger.info(
        f"[AgentTrace] conv={conversation_id} "
        f"tools={tools_used} iters={iterations} "
        f"duration={duration_ms}ms "
        f"msg_len={len(user_message)} resp_len={len(response)}"
    )
