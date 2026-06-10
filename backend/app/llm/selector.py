"""ModelSelector — 带 fallback 链的 Provider 选择器

移植自 OpenSquilla selector.py。
核心价值：primary 挂了自动切 fallback，用户无感。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .anthropic_provider import AnthropicProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .protocol import LLMProvider


@dataclass
class ProviderConfig:
    """单个 Provider 的运行时配置"""
    provider: str  # "openai" | "anthropic" | "ollama"
    model: str
    api_key: str = ""
    base_url: str = ""
    provider_kind: str = ""  # 用于 openai_compat 的细分（deepseek/moonshot/...）
    proxy: str = ""


@dataclass
class SelectorConfig:
    """完整的选择配置：primary + fallback 链"""
    primary: ProviderConfig
    fallbacks: list[ProviderConfig] = field(default_factory=list)


class ProviderBuildError(Exception):
    """Provider 实例化失败"""


def _build_provider(cfg: ProviderConfig) -> LLMProvider:
    """根据 ProviderConfig 实例化正确的 Provider 类"""
    provider = cfg.provider.lower()

    if provider == "anthropic":
        return AnthropicProvider(
            api_key=cfg.api_key,
            model=cfg.model,
            base_url=cfg.base_url or "https://api.anthropic.com",
            proxy=cfg.proxy or None,
        )

    if provider == "ollama":
        return OllamaProvider(
            model=cfg.model,
            base_url=cfg.base_url or "http://localhost:11434",
            proxy=cfg.proxy or None,
        )

    # 默认走 OpenAI 兼容（覆盖 openai/deepseek/moonshot/dashscope 等 20+ 家）
    kind = cfg.provider_kind or cfg.provider
    return OpenAIProvider(
        api_key=cfg.api_key,
        model=cfg.model,
        base_url=cfg.base_url or "https://api.openai.com/v1",
        provider_kind=kind,
        proxy=cfg.proxy or None,
    )


class ModelSelector:
    """带 fallback 链的 Provider 选择器

    用法::

        selector = ModelSelector(SelectorConfig(
            primary=ProviderConfig("openai", "gpt-4o", api_key="..."),
            fallbacks=[ProviderConfig("ollama", "llama3")],
        ))
        provider = selector.resolve()  # 返回 primary
        # 挂了之后调 selector.next_fallback() 切到下一个
    """

    def __init__(self, config: SelectorConfig) -> None:
        self._config = config
        self._chain: list[ProviderConfig] = [config.primary, *config.fallbacks]
        self._index = 0

    def resolve(self) -> LLMProvider:
        """返回当前 provider（首次调用返回 primary）"""
        return _build_provider(self._chain[self._index])

    @property
    def active_provider_id(self) -> str:
        """当前激活的 provider 标识"""
        return self._chain[self._index].provider

    def has_fallback(self) -> bool:
        """是否还有 fallback 可用"""
        return self._index < len(self._chain) - 1

    def next_fallback(self) -> LLMProvider:
        """切换到下一个 fallback

        Raises IndexError 如果没有更多 fallback。
        """
        if not self.has_fallback():
            raise IndexError("No more provider fallbacks available")
        self._index += 1
        return _build_provider(self._chain[self._index])

    def override_model(self, model: str) -> None:
        """运行时切换 primary 的模型"""
        if model and model != self._chain[0].model:
            self._chain[0] = ProviderConfig(
                provider=self._chain[0].provider,
                model=model,
                api_key=self._chain[0].api_key,
                base_url=self._chain[0].base_url,
                provider_kind=self._chain[0].provider_kind,
                proxy=self._chain[0].proxy,
            )

    def reset(self) -> None:
        """重置到 primary"""
        self._index = 0

    def clone(self) -> ModelSelector:
        """返回独立副本（并发安全）"""
        return ModelSelector(self._config)

    @property
    def current_config(self) -> ProviderConfig:
        return self._chain[self._index]


def build_provider(
    provider: str,
    model: str,
    api_key: str = "",
    base_url: str = "",
    provider_kind: str = "",
) -> LLMProvider:
    """便捷工厂：直接构建单个 Provider"""
    return _build_provider(ProviderConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider_kind=provider_kind,
    ))
