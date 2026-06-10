"""LLM Provider 统一类型定义 — 移植自 OpenSquilla

核心链路: StreamEvent → Provider.chat() → 前端渲染
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════
# Stream Events — 流式事件（核心）
# ═══════════════════════════════════════════════════════════

@dataclass
class TextDeltaEvent:
    """助手文本片段"""
    kind: Literal["text_delta"] = field(default="text_delta", init=False)
    text: str = ""


@dataclass
class ToolUseStartEvent:
    """LLM 开始一次工具调用"""
    kind: Literal["tool_use_start"] = field(default="tool_use_start", init=False)
    tool_use_id: str = ""
    tool_name: str = ""


@dataclass
class ToolUseDeltaEvent:
    """工具调用参数的流式 JSON 片段"""
    kind: Literal["tool_use_delta"] = field(default="tool_use_delta", init=False)
    tool_use_id: str = ""
    json_fragment: str = ""


@dataclass
class ToolUseEndEvent:
    """工具调用参数流完成"""
    kind: Literal["tool_use_end"] = field(default="tool_use_end", init=False)
    tool_use_id: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class DoneEvent:
    """流式完成"""
    kind: Literal["done"] = field(default="done", init=False)
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_content: str | None = None
    reasoning_tokens: int = 0
    cached_tokens: int = 0
    billed_cost: float = 0.0
    model: str = ""


@dataclass
class ErrorEvent:
    """流式错误"""
    kind: Literal["error"] = field(default="error", init=False)
    message: str = ""
    code: str = ""


StreamEvent = (
    TextDeltaEvent
    | ToolUseStartEvent
    | ToolUseDeltaEvent
    | ToolUseEndEvent
    | DoneEvent
    | ErrorEvent
)


# ═══════════════════════════════════════════════════════════
# Model Capabilities — 模型能力元数据
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ModelCapabilities:
    """模型能力标记"""
    supports_reasoning: bool = False
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    reasoning_format: str = "none"  # "none" | "deepseek" | "openai" | "gemini" | "think_tags"


# ═══════════════════════════════════════════════════════════
# Tool Definition — 工具定义
# ═══════════════════════════════════════════════════════════

class ToolParam(BaseModel):
    type: str
    description: str = ""
    enum: list[str] | None = None


class ToolInputSchema(BaseModel):
    type: Literal["object"] = "object"
    properties: dict[str, Any] = {}
    required: list[str] = []


class ToolDefinition(BaseModel):
    """传给 LLM 的工具定义"""
    name: str
    description: str
    input_schema: ToolInputSchema


# ═══════════════════════════════════════════════════════════
# Model Info — 模型信息
# ═══════════════════════════════════════════════════════════

class ModelInfo(BaseModel):
    """可用模型的元数据"""
    provider: str
    model_id: str
    display_name: str = ""
    context_window: int = 0
    max_output_tokens: int = 0
    supports_reasoning: bool = False
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0


# ═══════════════════════════════════════════════════════════
# Chat Config — 运行时配置
# ═══════════════════════════════════════════════════════════

class ChatConfig(BaseModel):
    """单次对话的运行时选项"""
    max_tokens: int = 16384
    temperature: float | None = None
    system: str | None = None
    stop_sequences: list[str] = []
    thinking: bool = False
    thinking_budget_tokens: int = 5000
    timeout: float = 120.0
    model_capabilities: ModelCapabilities | None = None
    tool_choice: Any | None = None


# ═══════════════════════════════════════════════════════════
# Message — 消息类型
# ═══════════════════════════════════════════════════════════

class ContentBlockText(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ContentBlockToolUse(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class ContentBlockToolResult(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str | list[Any]
    is_error: bool = False


class ContentBlockImage(BaseModel):
    type: Literal["image"] = "image"
    source_type: Literal["base64", "url"] = "base64"
    media_type: str
    data: str


class ContentBlockThinking(BaseModel):
    type: Literal["thinking"] = "thinking"
    thinking: str = ""


MessageContent = (
    str
    | list[
        ContentBlockText
        | ContentBlockToolUse
        | ContentBlockToolResult
        | ContentBlockImage
        | ContentBlockThinking
    ]
)


class Message(BaseModel):
    """单条对话消息"""
    role: Literal["user", "assistant"]
    content: MessageContent
    reasoning_content: str | None = None
