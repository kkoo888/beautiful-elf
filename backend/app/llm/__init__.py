"""LLM Provider 统一接入层

架构: DB 配置 → Runtime 桥梁 → Protocol + Selector → Provider 实现

核心链路:
  MySQL llm_provider 表
    → LLMRuntime.from_db_provider()
    → LLMProvider.chat()
    → AsyncIterator[StreamEvent]
    → 前端渲染

参考: OpenSquilla provider 层设计
"""

from .anthropic_provider import AnthropicProvider
from .failures import (
    ProviderFailureKind,
    ProviderRecoveryAction,
    classify_provider_error,
    decide_recovery_action,
)
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .protocol import LLMProvider, ProviderMetadata
from .runtime import LLMRuntime, ChatResult, llm_runtime
from .selector import (
    ModelSelector,
    ProviderBuildError,
    ProviderConfig,
    SelectorConfig,
    build_provider,
)
from .types import (
    ChatConfig,
    DoneEvent,
    ErrorEvent,
    Message,
    ModelCapabilities,
    ModelInfo,
    StreamEvent,
    TextDeltaEvent,
    ToolDefinition,
    ToolInputSchema,
    ToolUseDeltaEvent,
    ToolUseEndEvent,
    ToolUseStartEvent,
    ContentBlockText,
    ContentBlockToolResult,
    ContentBlockToolUse,
    dict_to_model_capabilities,
)

__all__ = [
    # Protocol
    "LLMProvider",
    "ProviderMetadata",
    # Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    # Selector
    "ModelSelector",
    "ProviderConfig",
    "SelectorConfig",
    "ProviderBuildError",
    "build_provider",
    # Runtime bridge
    "LLMRuntime",
    "ChatResult",
    "llm_runtime",
    # Types
    "ChatConfig",
    "Message",
    "ModelInfo",
    "ModelCapabilities",
    "ToolDefinition",
    "ToolInputSchema",
    "StreamEvent",
    "TextDeltaEvent",
    "ToolUseStartEvent",
    "ToolUseDeltaEvent",
    "ToolUseEndEvent",
    "DoneEvent",
    "ErrorEvent",
    "ContentBlockText",
    "ContentBlockToolUse",
    "ContentBlockToolResult",
    "dict_to_model_capabilities",
    # Failures
    "ProviderFailureKind",
    "ProviderRecoveryAction",
    "classify_provider_error",
    "decide_recovery_action",
]
