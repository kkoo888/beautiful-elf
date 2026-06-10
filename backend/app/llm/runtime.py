"""LLM Runtime — DB 配置 → OpenSquilla 运行时的桥梁

这是 beautiful-elf 独有的适配层：
  MySQL llm_provider 表 → ProviderConfig → ModelSelector → LLMProvider

管理那套（DB CRUD）不动，使用那套换成 Protocol + Selector 模式。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .protocol import LLMProvider
from .selector import ModelSelector, ProviderConfig, SelectorConfig, build_provider
from .types import (
    ChatConfig,
    DoneEvent,
    ErrorEvent,
    Message,
    TextDeltaEvent,
    ToolDefinition,
    ToolInputSchema,
    ContentBlockText,
)

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    """非流式对话结果"""
    content: str = ""
    model: str = ""
    provider_type: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_content: str | None = None
    error: str = ""

logger = logging.getLogger(__name__)

# DB provider_type → OpenSquilla provider / provider_kind 映射
_PROVIDER_TYPE_MAP: dict[str, tuple[str, str]] = {
    # (provider, provider_kind)
    "openai": ("openai", "openai"),
    "deepseek": ("openai", "deepseek"),
    "anthropic": ("anthropic", "anthropic"),
    "ollama": ("ollama", "ollama"),
    "moonshot": ("openai", "moonshot"),
    "dashscope": ("openai", "dashscope"),
    "qwen": ("openai", "dashscope"),
    "gemini": ("openai", "gemini"),
    "mistral": ("openai", "mistral"),
    "groq": ("openai", "groq"),
    "zhipu": ("openai", "zhipu"),
    "qianfan": ("openai", "qianfan"),
    "siliconflow": ("openai", "siliconflow"),
    "volcengine": ("openai", "volcengine"),
    "byteplus": ("openai", "byteplus"),
    "openrouter": ("openai", "openrouter"),
    "custom": ("openai", "custom"),
}


def _map_provider_type(provider_type: str) -> tuple[str, str]:
    """DB provider_type → (provider, provider_kind)

    未识别的类型默认走 openai 兼容。
    """
    key = provider_type.lower().strip()
    return _PROVIDER_TYPE_MAP.get(key, ("openai", key))


class LLMRuntime:
    """从 DB 配置构建 LLMProvider 运行时

    用法::

        runtime = LLMRuntime()
        provider = runtime.from_db_provider(db_provider)
        async for event in provider.chat(messages, tools, config):
            if isinstance(event, TextDeltaEvent):
                print(event.text, end="")
    """

    def from_db_provider(self, db_provider: Any, model_name: str = "") -> LLMProvider:
        """从 DB 的 LLMProvider ORM 对象构建运行时 Provider

        Args:
            db_provider: SQLAlchemy LLMProvider 模型实例
            model_name: 模型名称（为空时用 provider 默认）
        """
        provider_type = getattr(db_provider, "provider_type", "custom")
        base_url = getattr(db_provider, "base_url", "") or ""
        api_key = getattr(db_provider, "api_key", "") or ""

        provider, kind = _map_provider_type(provider_type)

        # Ollama 不需要 api_key
        if provider == "ollama":
            return build_provider(
                provider="ollama",
                model=model_name or "llama3",
                base_url=base_url,
            )

        return build_provider(
            provider=provider,
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            provider_kind=kind,
        )

    def build_selector(
        self,
        primary_provider: Any,
        primary_model: str,
        fallback_providers: list[tuple[Any, str]] | None = None,
    ) -> ModelSelector:
        """构建带 fallback 的 ModelSelector

        Args:
            primary_provider: 主 provider 的 DB ORM 对象
            primary_model: 主模型名
            fallback_providers: [(db_provider, model_name), ...] 备选列表
        """
        primary_cfg = self._db_to_config(primary_provider, primary_model)
        fallback_cfgs = [
            self._db_to_config(p, m) for p, m in (fallback_providers or [])
        ]
        return ModelSelector(SelectorConfig(primary=primary_cfg, fallbacks=fallback_cfgs))

    def _db_to_config(self, db_provider: Any, model_name: str) -> ProviderConfig:
        """DB ORM → ProviderConfig"""
        provider_type = getattr(db_provider, "provider_type", "custom")
        base_url = getattr(db_provider, "base_url", "") or ""
        api_key = getattr(db_provider, "api_key", "") or ""

        provider, kind = _map_provider_type(provider_type)

        return ProviderConfig(
            provider=provider,
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            provider_kind=kind,
        )

    async def chat(
        self,
        provider: LLMProvider,
        messages: list[dict[str, str]],
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResult:
        """非流式对话 — 收集全部 StreamEvent 后返回结果

        Args:
            provider: LLMProvider 实例
            messages: [{"role": "user", "content": "..."}]
            system: 系统提示词
            temperature: 温度
            max_tokens: 最大 token
        """
        # dict → Message 对象
        llm_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system = content
                continue
            llm_messages.append(Message(role=role, content=content))

        config = ChatConfig(
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or None,
        )

        result = ChatResult()
        text_parts = []
        reasoning_parts = []

        try:
            async for event in provider.chat(llm_messages, config=config):
                if isinstance(event, TextDeltaEvent):
                    text_parts.append(event.text)
                elif isinstance(event, DoneEvent):
                    result.model = event.model
                    result.input_tokens = event.input_tokens
                    result.output_tokens = event.output_tokens
                    result.reasoning_content = event.reasoning_content
                elif isinstance(event, ErrorEvent):
                    result.error = event.message
        except Exception as e:
            result.error = str(e)

        result.content = "".join(text_parts)
        if result.reasoning_content is None and reasoning_parts:
            result.reasoning_content = "".join(reasoning_parts)

        return result


# 全局单例
llm_runtime = LLMRuntime()
