"""ContextBudgetGovernor — 上下文预算治理器

根据模型 context_window 自动计算各层预算，防止 context overflow。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger

log = get_logger(__name__)

CHARS_PER_TOKEN = 4
CONTEXT_RESERVE_FLOOR_TOKENS = 20_000


@dataclass(frozen=True)
class ContextBudgetSnapshot:
    """预算快照"""
    context_window_tokens: int
    reserved_tokens: int
    usable_tokens: int
    max_chars: int               # 给 LLM 的最大字符数
    max_rag_result_chars: int    # RAG 检索结果最大字符数
    max_tool_result_chars: int   # 工具返回结果最大字符数
    threshold: float             # 安全阈值 (0.85)


class ContextBudgetGovernor:
    """上下文预算治理器

    从模型 context_window 推导出各层预算：
    - usable_tokens = context_window - reserved (输出+thinking预留)
    - max_chars = usable_tokens × threshold × 4 (字符)
    - RAG/tool 结果按比例分配

    用法:
        governor = ContextBudgetGovernor.from_values(
            context_window_tokens=128000,
            max_output_tokens=4096,
        )
        snapshot = governor.snapshot()
        # 用 snapshot.max_rag_result_chars 裁剪 RAG 结果
    """

    def __init__(
        self,
        context_window_tokens: int = 128000,
        max_output_tokens: int = 4096,
        thinking_budget_tokens: int = 0,
        threshold: float = 0.85,
    ):
        self._context_window = max(1, context_window_tokens)
        self._max_output = max(0, max_output_tokens)
        self._thinking_budget = max(0, thinking_budget_tokens)
        self._threshold = min(max(threshold, 0.1), 0.95)
        self._snapshot = self._compute()

    @classmethod
    def from_config(cls, config) -> "ContextBudgetGovernor":
        """从项目配置创建"""
        return cls(
            context_window_tokens=getattr(config, "context_window_tokens", 128000),
            max_output_tokens=getattr(config, "max_output_tokens", 4096),
            thinking_budget_tokens=getattr(config, "thinking_budget_tokens", 0),
            threshold=getattr(config, "context_overflow_threshold", 0.85),
        )

    @classmethod
    def from_values(cls, **kwargs) -> "ContextBudgetGovernor":
        """从参数创建"""
        return cls(**kwargs)

    def _compute(self) -> ContextBudgetSnapshot:
        """计算预算分配"""
        ctx = self._context_window
        max_reserve = max(1, ctx // 2)
        output_reserve = min(self._max_output + self._thinking_budget, max_reserve)
        context_reserve = (
            CONTEXT_RESERVE_FLOOR_TOKENS
            if ctx >= 64_000
            else max(512, ctx // 8)
        )
        reserved = min(ctx - 1, output_reserve + context_reserve)
        usable = max(1, ctx - reserved)
        max_chars = int(usable * self._threshold * CHARS_PER_TOKEN)

        # RAG 结果：占可用上下文的 50%（留空间给 system prompt + 对话历史）
        max_rag_chars = max(4_000, min(
            max_chars // 2,
            160_000 if ctx >= 64_000 else 32_000,
        ))

        # 工具结果：占可用上下文的 25%
        max_tool_chars = max(2_000, min(
            max_chars // 4,
            80_000 if ctx >= 64_000 else 16_000,
        ))

        return ContextBudgetSnapshot(
            context_window_tokens=ctx,
            reserved_tokens=reserved,
            usable_tokens=usable,
            max_chars=max_chars,
            max_rag_result_chars=max_rag_chars,
            max_tool_result_chars=max_tool_chars,
            threshold=self._threshold,
        )

    def snapshot(self) -> ContextBudgetSnapshot:
        return self._snapshot

    def update_window(self, context_window_tokens: int, max_output_tokens: int = 4096):
        """动态更新窗口大小（模型切换时）"""
        self._context_window = max(1, context_window_tokens)
        self._max_output = max(0, max_output_tokens)
        self._snapshot = self._compute()
        log.info(
            f"[budget] 预算更新: window={self._context_window}, "
            f"usable={self._snapshot.usable_tokens}, "
            f"max_chars={self._snapshot.max_chars}"
        )
