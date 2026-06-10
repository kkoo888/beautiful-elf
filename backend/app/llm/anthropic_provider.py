"""AnthropicProvider — Anthropic Claude API 的统一流式 Provider

移植自 OpenSquilla anthropic.py，保留核心 SSE 解析和 thinking 支持。
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

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
    ToolUseDeltaEvent,
    ToolUseEndEvent,
    ToolUseStartEvent,
)

_ANTHROPIC_VERSION = "2023-06-01"
_ANTHROPIC_API_BASE = "https://api.anthropic.com"


def _coerce_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _build_tool_payload(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema.model_dump(exclude_none=True),
    }


def _build_message_payload(msg: Message, model: str | None = None) -> dict[str, Any]:
    """将 Message 转为 Anthropic 格式"""
    if isinstance(msg.content, str):
        return {"role": msg.role, "content": msg.content}

    blocks: list[dict[str, Any]] = []
    for block in msg.content:
        if block.type == "text":
            blocks.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            blocks.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
        elif block.type == "tool_result":
            content = block.content if isinstance(block.content, str) else json.dumps(block.content)
            result_block: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": block.tool_use_id,
                "content": content,
            }
            if block.is_error:
                result_block["is_error"] = True
            blocks.append(result_block)
        elif block.type == "image":
            blocks.append({
                "type": "image",
                "source": {
                    "type": block.source_type,
                    "media_type": block.media_type,
                    "data": block.data if block.source_type == "base64" else "",
                    "url": block.data if block.source_type == "url" else "",
                },
            })

    return {"role": msg.role, "content": blocks}


def _build_system_payload(cfg: ChatConfig) -> str | list[dict[str, Any]] | None:
    if not cfg.system:
        return None
    return cfg.system


class AnthropicProvider:
    """Anthropic Claude API 的流式 Provider"""

    provider_name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: str = _ANTHROPIC_API_BASE,
        proxy: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._proxy = proxy or None

    @property
    def model(self) -> str:
        return self._model

    def _api_url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        config: ChatConfig | None = None,
    ) -> AsyncIterator[StreamEvent]:
        cfg = config or ChatConfig()
        return self._stream(messages, tools, cfg)

    async def _stream(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None,
        cfg: ChatConfig,
    ) -> AsyncIterator[StreamEvent]:
        max_tokens = max(1, cfg.max_tokens)

        # Thinking 配置
        thinking_payload: dict[str, Any] | None = None
        if cfg.thinking:
            budget_tokens = max(1, cfg.thinking_budget_tokens)
            if budget_tokens >= max_tokens:
                max_tokens = budget_tokens + 4096
            thinking_payload = {"type": "enabled", "budget_tokens": budget_tokens}

        built_messages = [_build_message_payload(m, model=self._model) for m in messages]

        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": built_messages,
            "stream": True,
        }

        system_payload = _build_system_payload(cfg)
        if system_payload:
            payload["system"] = system_payload
        if cfg.temperature is not None and not cfg.thinking:
            payload["temperature"] = cfg.temperature
        if cfg.stop_sequences:
            payload["stop_sequences"] = cfg.stop_sequences
        if tools:
            payload["tools"] = [_build_tool_payload(t) for t in tools]
        if thinking_payload:
            payload["thinking"] = thinking_payload

        headers = {
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
            "accept": "text/event-stream",
            "x-api-key": self._api_key,
        }

        # Tool 状态追踪
        tool_buffers: dict[str, list[str]] = {}
        tool_names: dict[str, str] = {}
        index_to_tid: dict[int, str] = {}
        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0
        thinking_parts: list[str] = []
        thinking_signature: str | None = None
        stop_reason = "end_turn"

        try:
            async with httpx.AsyncClient(
                timeout=cfg.timeout,
                proxy=self._proxy,
            ) as client:
                async with client.stream(
                    "POST",
                    self._api_url("/v1/messages"),
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        body_text = body.decode("utf-8", errors="replace")
                        try:
                            err_json = json.loads(body_text)
                            err_msg = err_json.get("error", {}).get("message", body_text)
                        except json.JSONDecodeError:
                            err_msg = body_text
                        yield ErrorEvent(
                            message=f"HTTP {response.status_code}: {err_msg}",
                            code=str(response.status_code),
                        )
                        return

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        etype = event.get("type", "")

                        if etype == "message_start":
                            usage = event.get("message", {}).get("usage", {})
                            input_tokens = _coerce_int(usage.get("input_tokens"))
                            cached_tokens = _coerce_int(usage.get("cache_read_input_tokens"))

                        elif etype == "content_block_start":
                            index = event.get("index", -1)
                            block = event.get("content_block", {})
                            if block.get("type") == "tool_use":
                                tid = block["id"]
                                tname = block["name"]
                                tool_buffers[tid] = []
                                tool_names[tid] = tname
                                index_to_tid[index] = tid
                                yield ToolUseStartEvent(tool_use_id=tid, tool_name=tname)

                        elif etype == "content_block_delta":
                            delta = event.get("delta", {})
                            dtype = delta.get("type")
                            if dtype == "text_delta":
                                yield TextDeltaEvent(text=delta.get("text", ""))
                            elif dtype == "input_json_delta":
                                index = event.get("index", 0)
                                fragment = delta.get("partial_json", "")
                                tid = index_to_tid.get(index)
                                if tid is not None:
                                    tool_buffers[tid].append(fragment)
                                    yield ToolUseDeltaEvent(tool_use_id=tid, json_fragment=fragment)
                            elif dtype == "thinking_delta":
                                thinking_parts.append(delta.get("thinking", ""))
                            elif dtype == "signature_delta":
                                thinking_signature = delta.get("signature") or thinking_signature

                        elif etype == "content_block_stop":
                            index = event.get("index", -1)
                            tid = index_to_tid.get(index)
                            if tid is not None:
                                full_json = "".join(tool_buffers[tid])
                                try:
                                    args = json.loads(full_json) if full_json else {}
                                except json.JSONDecodeError:
                                    args = {"_raw": full_json}
                                yield ToolUseEndEvent(
                                    tool_use_id=tid,
                                    tool_name=tool_names.get(tid, ""),
                                    arguments=args,
                                )

                        elif etype == "message_delta":
                            usage = event.get("usage", {})
                            output_tokens = _coerce_int(usage.get("output_tokens"))
                            cached_tokens = max(cached_tokens, _coerce_int(usage.get("cache_read_input_tokens")))
                            stop_reason = event.get("delta", {}).get("stop_reason", "end_turn")

                        elif etype == "message_stop":
                            reasoning_content = "".join(thinking_parts) or None
                            yield DoneEvent(
                                stop_reason=stop_reason,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                reasoning_content=reasoning_content,
                                cached_tokens=cached_tokens,
                            )

        except httpx.TimeoutException as exc:
            yield ErrorEvent(message=f"Request timed out: {exc}", code="timeout")
        except httpx.RequestError as exc:
            yield ErrorEvent(message=f"Request error: {exc}", code="request_error")

    async def list_models(self) -> list[ModelInfo]:
        """Anthropic 不提供模型列表 API，返回已知模型"""
        known = [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-3-5-haiku-20241022",
        ]
        return [
            ModelInfo(provider="anthropic", model_id=m, display_name=m)
            for m in known
        ]
