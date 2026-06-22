"""API 错误分类器 — 结构化错误分类 + 恢复策略（对标 Hermes Agent）

提供结构化的 API 错误分类和优先级排序的分类管道，
确定正确的恢复动作（重试、轮换凭证、切换 provider、压缩上下文、终止）。

替代散落的 inline 字符串匹配，集中分类器供重试循环查询。
"""
from __future__ import annotations
import enum
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ── 错误分类枚举 ─────────────────────────────────────────

class FailoverReason(enum.Enum):
    """API 调用失败原因 — 决定恢复策略"""
    auth = "auth"                          # 临时认证失败（401/403）→ 刷新/轮换
    auth_permanent = "auth_permanent"      # 认证永久失败 → 终止
    billing = "billing"                    # 402 或额度耗尽 → 立即轮换
    rate_limit = "rate_limit"              # 429 或配额限流 → 退避后轮换
    overloaded = "overloaded"              # 503/529 → 退避重试
    server_error = "server_error"          # 500/502 → 重试
    timeout = "timeout"                    # 连接/读取超时 → 重建客户端重试
    context_overflow = "context_overflow"  # 上下文过大 → 压缩，不是 failover
    payload_too_large = "payload_too_large"  # 413 → 压缩 payload
    model_not_found = "model_not_found"    # 404 或无效模型 → 切换模型
    content_policy_blocked = "content_policy_blocked"  # 安全过滤 → 不重试同样请求
    format_error = "format_error"          # 400 请求格式错误 → 修复或终止
    unknown = "unknown"                    # 无法分类 → 退避重试


# ── 分类结果 ──────────────────────────────────────────────

@dataclass
class ClassifiedError:
    """结构化错误分类 + 恢复提示"""
    reason: FailoverReason
    status_code: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    message: str = ""
    error_context: Dict[str, Any] = field(default_factory=dict)

    # 恢复动作提示
    retryable: bool = True
    should_compress: bool = False
    should_rotate_credential: bool = False
    should_fallback: bool = False
    max_retries: int = 3

    @property
    def is_auth(self) -> bool:
        return self.reason in {FailoverReason.auth, FailoverReason.auth_permanent}


# ── 错误模式匹配 ─────────────────────────────────────────

_BILLING_PATTERNS = [
    "insufficient credits", "insufficient_quota", "insufficient balance",
    "credit balance", "credits exhausted", "no usable credits",
    "top up your credits", "payment required", "billing hard limit",
    "exceeded your current quota", "account is deactivated",
    "out of funds", "balance_depleted", "model_not_supported_on_free_tier",
]

_RATE_LIMIT_PATTERNS = [
    "rate limit", "rate_limit", "too many requests", "throttled",
    "requests per minute", "tokens per minute", "requests per day",
    "try again in", "please retry after", "resource_exhausted",
    "throttlingexception", "too many concurrent requests",
]

_CONTEXT_OVERFLOW_PATTERNS = [
    "context length", "context size", "maximum context", "token limit",
    "too many tokens", "reduce the length", "exceeds the limit",
    "context window", "prompt is too long", "prompt exceeds max length",
    "maximum number of tokens", "exceeds the max_model_len",
    "context length exceeded", "truncating input",
    "超过最大长度", "上下文长度",
]

_AUTH_PATTERNS = [
    "invalid api key", "invalid_api_key", "authentication",
    "unauthorized", "forbidden", "invalid token", "token expired",
    "token revoked", "access denied",
]

_MODEL_NOT_FOUND_PATTERNS = [
    "is not a valid model", "invalid model", "model not found",
    "model_not_found", "does not exist", "no such model", "unknown model",
]

_CONTENT_POLICY_PATTERNS = [
    "flagged for possible cybersecurity risk", "violates our usage policies",
    "your request was flagged by", "prompt was flagged by our safety",
    "content_filter", "responsibleaipolicyviolation",
]

_FORMAT_ERROR_PATTERNS = [
    "unknown parameter", "unsupported parameter", "unrecognized request argument",
    "invalid_request_error", "invalid tool call arguments",
]

_PAYLOAD_TOO_LARGE_PATTERNS = [
    "request entity too large", "payload too large", "error code: 413",
]


def _match_patterns(text: str, patterns: list[str]) -> bool:
    """检查文本是否匹配任何模式"""
    text_lower = text.lower()
    return any(p in text_lower for p in patterns)


# ── 分类管道 ──────────────────────────────────────────────

def classify_error(
    error: Exception,
    provider: str = "",
    model: str = "",
) -> ClassifiedError:
    """优先级排序的错误分类管道

    Args:
        error: 原始异常
        provider: 供应商名
        model: 模型名

    Returns:
        ClassifiedError 带恢复策略提示
    """
    status_code = getattr(error, "status_code", None)
    body = ""
    if hasattr(error, "body"):
        if isinstance(error.body, dict):
            body = str(error.body.get("error", {}).get("message", ""))
        elif isinstance(error.body, str):
            body = error.body
    message = str(error) + " " + body

    ctx = {"raw_message": str(error)[:500], "provider": provider, "model": model}

    # 1. 认证错误
    if status_code in (401, 403) or _match_patterns(message, _AUTH_PATTERNS):
        return ClassifiedError(
            reason=FailoverReason.auth, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=True,
            should_rotate_credential=True, max_retries=1,
        )

    # 2. 额度耗尽（不是限流）
    if status_code == 402 or _match_patterns(message, _BILLING_PATTERNS):
        return ClassifiedError(
            reason=FailoverReason.billing, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=False,
            should_rotate_credential=True, should_fallback=True,
        )

    # 3. 限流
    if status_code == 429 or _match_patterns(message, _RATE_LIMIT_PATTERNS):
        return ClassifiedError(
            reason=FailoverReason.rate_limit, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=True,
            should_rotate_credential=True, max_retries=5,
        )

    # 4. 上下文溢出
    if _match_patterns(message, _CONTEXT_OVERFLOW_PATTERNS):
        return ClassifiedError(
            reason=FailoverReason.context_overflow, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=True,
            should_compress=True, max_retries=1,
        )

    # 5. Payload 过大
    if status_code == 413 or _match_patterns(message, _PAYLOAD_TOO_LARGE_PATTERNS):
        return ClassifiedError(
            reason=FailoverReason.payload_too_large, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=True,
            should_compress=True, max_retries=1,
        )

    # 6. 安全过滤
    if _match_patterns(message, _CONTENT_POLICY_PATTERNS):
        return ClassifiedError(
            reason=FailoverReason.content_policy_blocked, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=False,
            should_fallback=True,
        )

    # 7. 模型不存在
    if status_code == 404 or _match_patterns(message, _MODEL_NOT_FOUND_PATTERNS):
        return ClassifiedError(
            reason=FailoverReason.model_not_found, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=False,
            should_fallback=True,
        )

    # 8. 格式错误
    if status_code == 400 or _match_patterns(message, _FORMAT_ERROR_PATTERNS):
        return ClassifiedError(
            reason=FailoverReason.format_error, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=False,
        )

    # 9. 服务过载
    if status_code in (503, 529):
        return ClassifiedError(
            reason=FailoverReason.overloaded, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=True, max_retries=3,
        )

    # 10. 服务器错误
    if status_code and status_code >= 500:
        return ClassifiedError(
            reason=FailoverReason.server_error, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=True, max_retries=3,
        )

    # 11. 超时
    if "timeout" in message.lower() or "timed out" in message.lower():
        return ClassifiedError(
            reason=FailoverReason.timeout, status_code=status_code,
            provider=provider, model=model, message=message[:300],
            error_context=ctx, retryable=True, max_retries=2,
        )

    # 12. 未知
    return ClassifiedError(
        reason=FailoverReason.unknown, status_code=status_code,
        provider=provider, model=model, message=message[:300],
        error_context=ctx, retryable=True, max_retries=2,
    )
