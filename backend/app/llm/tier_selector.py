"""Tier Selector — 按模型层级选择 LLM 实例（借鉴 OpenSquilla ModelSelector）

维护 c0/c1/c2 三个 LLM 实例，按 tier 返回对应的最经济模型。

设计参考：OpenSquilla provider/selector.py + router_tiers.py
"""
from __future__ import annotations

from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class TierSelector:
    """模型层级选择器

    用法::

        selector = TierSelector()
        selector.register("c0", cheap_llm)     # qwen3:7b / gpt-4o-mini
        selector.register("c1", default_llm)   # deepseek-chat
        selector.register("c2", strong_llm)    # gpt-4o / claude-4

        llm = selector.get_llm("c0")  # → cheap_llm
    """

    def __init__(self):
        self._llms: dict[str, object] = {}  # tier → LLM instance
        self._model_names: dict[str, str] = {}  # tier → model name (用于日志)

    def register(self, tier: str, llm: object, model_name: str = ""):
        """注册某个 tier 的 LLM

        Args:
            tier: "c0" / "c1" / "c2"
            llm: LangChain BaseChatModel 实例（或任何支持 ainvoke 的对象）
            model_name: 模型名称（用于日志）
        """
        self._llms[tier] = llm
        self._model_names[tier] = model_name or tier
        logger.info(f"[tier_selector] 注册 {tier} → {model_name or 'unnamed'}")

    def get_llm(self, tier: str = "c1") -> object:
        """按 tier 获取 LLM 实例

        降级策略：c2 → c1 → 返回第一个可用的
        """
        llm = self._llms.get(tier)
        if llm:
            return llm

        # 降级
        fallback_order = ["c1", "c0", "c2"]
        for fallback in fallback_order:
            llm = self._llms.get(fallback)
            if llm:
                logger.warning(f"[tier_selector] {tier} 未注册，降级到 {fallback}")
                return llm

        raise RuntimeError(f"[tier_selector] 没有任何已注册的 LLM（请求 tier={tier}）")

    def get_model_name(self, tier: str) -> str:
        """获取某个 tier 的模型名称"""
        return self._model_names.get(tier, "unknown")

    def has_tier(self, tier: str) -> bool:
        """检查某个 tier 是否已注册"""
        return tier in self._llms

    @property
    def registered_tiers(self) -> list[str]:
        """返回所有已注册的 tier 列表"""
        return list(self._llms.keys())
