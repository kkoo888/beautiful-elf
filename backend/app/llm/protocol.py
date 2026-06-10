"""LLMProvider Protocol — 统一 LLM 接口契约

移植自 OpenSquilla protocol.py，去掉 OpenClaw 特有依赖。
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .types import ChatConfig, Message, ModelInfo, StreamEvent, ToolDefinition


@dataclass(frozen=True)
class ProviderMetadata:
    """Provider 只读元数据（不含密钥）"""
    provider_name: str = ""
    provider_kind: str = ""
    model: str = ""
    base_url: str = ""


@dataclass(frozen=True)
class ProviderConnectionConfig:
    """Provider 内部连接配置"""
    provider_kind: str = ""
    model: str = ""
    api_key: str = field(default="", repr=False)
    base_url: str = ""


@runtime_checkable
class LLMProvider(Protocol):
    """统一异步流式接口 — 所有 Provider 必须实现

    实现者需提供:
    - chat(): 流式返回一个对话轮次的事件
    - list_models(): 返回该 provider 可用的模型列表
    - provider_name: str 标识符
    """

    provider_name: str

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        config: ChatConfig | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """流式对话 — 按顺序 yield StreamEvent

        - TextDeltaEvent: 文本片段
        - ToolUseStartEvent / ToolUseDeltaEvent / ToolUseEndEvent: 工具调用
        - DoneEvent: 对话完成
        - ErrorEvent: 出错（不抛异常）
        """
        ...

    async def list_models(self) -> list[ModelInfo]:
        """返回该 provider 可用的模型列表"""
        ...
