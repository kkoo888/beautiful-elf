"""OpenAIProvider — OpenAI 兼容 API 的统一流式 Provider

覆盖: OpenAI, DeepSeek, Moonshot, DashScope(通义), Gemini, Mistral, Groq,
      智谱, 硅基流动, 火山引擎, BytePlus, 以及所有 OpenAI 兼容接口。

移植自 OpenSquilla openai.py，去掉 OpenClaw/MiniMax/OpenRouter 特有逻辑。
"""
from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx

from app.core.logging import get_logger
from .protocol import ProviderConnectionConfig, ProviderMetadata
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

logger = get_logger(__name__)

_OPENAI_API_BASE = "https://api.openai.com"


# ═══════════════════════════════════════════════════════════
# 内部工具函数
# ═══════════════════════════════════════════════════════════

def _coerce_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _usage_fields(usage: dict[str, Any] | None) -> tuple[int, int, int, int]:
    """提取 usage 字段 → (input_tokens, output_tokens, reasoning_tokens, cached_tokens)"""
    if not usage:
        return 0, 0, 0, 0
    input_tokens = _coerce_int(usage.get("total_tokens")) or (
        _coerce_int(usage.get("prompt_tokens"))
        + _coerce_int(usage.get("cached_tokens"))
    )
    output_tokens = _coerce_int(usage.get("completion_tokens"))
    reasoning_tokens = _coerce_int(usage.get("completion_tokens_details", {}).get("reasoning_tokens"))
    cached_tokens = _coerce_int(usage.get("cached_tokens") or usage.get("prompt_tokens_details", {}).get("cached_tokens"))
    return input_tokens, output_tokens, reasoning_tokens, cached_tokens


def _should_send_temperature(provider_kind: str, model: str, cfg: ChatConfig, caps: ModelCapabilities | None) -> bool:
    """某些模型不支持 temperature（如 o1/o3 系列）"""
    if cfg.thinking and caps and caps.supports_reasoning:
        return False
    model_l = model.lower()
    if model_l.startswith(("o1", "o3", "o4")):
        return False
    return cfg.temperature is not None


def _build_openai_tool(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema.model_dump(exclude_none=True),
        },
    }


def _build_openai_messages(msg: Message, include_reasoning: bool = False) -> list[dict[str, Any]]:
    """将 Message 转为 OpenAI 格式（可能拆出多条）"""
    if isinstance(msg.content, str):
        result: dict[str, Any] = {"role": msg.role, "content": msg.content}
        if include_reasoning and msg.reasoning_content and msg.role == "assistant":
            result["reasoning_content"] = msg.reasoning_content
        return [result]

    blocks: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []

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
            tool_results.append({
                "role": "tool",
                "tool_call_id": block.tool_use_id,
                "content": content,
            })
        elif block.type == "image":
            blocks.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{block.media_type};base64,{block.data}"
                    if block.source_type == "base64"
                    else block.data
                },
            })

    # tool_result 单独作为 tool 消息
    if tool_results:
        return tool_results

    if len(blocks) == 1 and blocks[0].get("type") == "text":
        result = {"role": msg.role, "content": blocks[0]["text"]}
        if include_reasoning and msg.reasoning_content and msg.role == "assistant":
            result["reasoning_content"] = msg.reasoning_content
        return [result]

    result = {"role": msg.role, "content": blocks}
    if include_reasoning and msg.reasoning_content and msg.role == "assistant":
        result["reasoning_content"] = msg.reasoning_content
    return [result]


def _resolve_tool_call_index(tc: dict, pending_calls: dict) -> int:
    """解析 tool_call 的索引"""
    idx = tc.get("index")
    if idx is not None:
        return int(idx)
    # 某些 provider 不给 index，用 id 匹配
    tc_id = tc.get("id", "")
    for k, v in pending_calls.items():
        if v["id"] == tc_id:
            return k
    return len(pending_calls)


def _stream_timeout(timeout: float) -> httpx.Timeout:
    """流式请求的超时配置"""
    return httpx.Timeout(timeout, connect=10.0)


def _extract_think_tags(text: str) -> str:
    """从文本中提取 <think> 标签内容"""
    match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


# ═══════════════════════════════════════════════════════════
# Provider 实现
# ═══════════════════════════════════════════════════════════

class OpenAIProvider:
    """OpenAI 兼容 API 的流式 Provider

    通过 base_url + provider_kind 适配 20+ 家服务商。
    """

    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = _OPENAI_API_BASE,
        provider_kind: str = "openai",
        org_id: str | None = None,
        proxy: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._provider_kind = provider_kind
        self._org_id = org_id
        self._proxy = proxy or None

    @property
    def model(self) -> str:
        return self._model

    def provider_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=self.provider_name,
            provider_kind=self._provider_kind,
            model=self._model,
            base_url=self._base_url,
        )

    def provider_connection_config(self) -> ProviderConnectionConfig:
        return ProviderConnectionConfig(
            provider_kind=self._provider_kind,
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
        )

    def _api_url(self, path: str) -> str:
        """构建 API URL，避免重复 /v1 前缀"""
        for suffix in ("/v1", "/v2", "/v3", "/v4"):
            if self._base_url.endswith(suffix) and path.startswith("/v1/"):
                return f"{self._base_url}{path[3:]}"
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
        # ── 构建消息 ──
        openai_messages: list[dict[str, Any]] = []
        caps = cfg.model_capabilities

        if cfg.system:
            openai_messages.append({"role": "system", "content": cfg.system})

        for m in messages:
            openai_messages.extend(_build_openai_messages(m))

        # ── 构建 payload ──
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": openai_messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        # max_tokens vs max_completion_tokens（硬上限保护：防止超限 500）
        _mt = cfg.max_tokens
        if _mt and _mt > 65536:
            logger.warning(f"[openai_provider] max_tokens={_mt} 超过 65536 上限，自动截断")
            _mt = 65536
        model_l = self._model.lower()
        if model_l.startswith(("o1", "o3", "o4")):
            payload["max_completion_tokens"] = _mt
        else:
            payload["max_tokens"] = _mt

        if _should_send_temperature(self._provider_kind, self._model, cfg, caps):
            payload["temperature"] = cfg.temperature

        if cfg.stop_sequences:
            payload["stop"] = cfg.stop_sequences

        if tools:
            payload["tools"] = [_build_openai_tool(t) for t in tools]

        if cfg.tool_choice is not None:
            tc = cfg.tool_choice
            # langchain-openai 官方: string tool_choice → dict 格式
            # "auto"/"none"/"required" 保持不变; 函数名 → {"type":"function","function":{"name":...}}
            if isinstance(tc, str) and tc not in ("auto", "none", "required"):
                tool_names = [t.get("function", {}).get("name", "") for t in payload.get("tools", [])]
                if tc in tool_names:
                    tc = {"type": "function", "function": {"name": tc}}
            payload["tool_choice"] = tc

        # ── 日志：打印实际 HTTP payload 关键字段 ──
        logger.info(f"[openai_provider] PAYLOAD: model={payload.get('model')} stream={payload.get('stream')} tool_choice={payload.get('tool_choice')} msg_count={len(payload.get('messages', []))}")

        # ── Reasoning 模式注入 ──
        if caps and caps.supports_reasoning and cfg.thinking:
            if caps.reasoning_format == "deepseek":
                payload["thinking"] = {"type": "enabled"}
            elif caps.reasoning_format == "openai":
                effort = "high" if cfg.thinking_budget_tokens > 10000 else "medium"
                payload["reasoning_effort"] = effort
            elif caps.reasoning_format == "gemini":
                payload["reasoning_effort"] = "high"
        elif caps and caps.supports_reasoning and not cfg.thinking:
            if caps.reasoning_format == "deepseek":
                payload["thinking"] = {"type": "disabled"}
            elif caps.reasoning_format == "gemini":
                payload["reasoning_effort"] = "none"

        # ── HTTP 请求 ──
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if self._org_id:
            headers["OpenAI-Organization"] = self._org_id

        pending_calls: dict[int, dict[str, Any]] = {}
        reasoning_parts: list[str] = []
        assistant_text_parts: list[str] = []
        input_tokens = 0
        output_tokens = 0
        reasoning_tokens = 0
        cached_tokens = 0
        actual_model = self._model
        stop_reason = "stop"

        try:
            async with httpx.AsyncClient(
                timeout=_stream_timeout(cfg.timeout),
                proxy=self._proxy,
            ) as client:
                async with client.stream(
                    "POST",
                    self._api_url("/v1/chat/completions"),
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        body_text = body.decode("utf-8", errors="replace")
                        # 尝试提取结构化错误信息
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

                    # ── SSE 流式解析 ──
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if chunk.get("model"):
                            actual_model = chunk["model"]

                        # Usage（可能在最后一个 chunk）
                        if chunk.get("usage"):
                            input_tokens, output_tokens, reasoning_tokens, cached_tokens = (
                                _usage_fields(chunk["usage"])
                            )

                        for choice in chunk.get("choices", []):
                            finish = choice.get("finish_reason")
                            if finish:
                                stop_reason = finish

                            delta = choice.get("delta", {})

                            # 文本内容
                            text = delta.get("content")
                            if text:
                                yield TextDeltaEvent(text=text)
                                assistant_text_parts.append(text)

                            # Reasoning content（DeepSeek / OpenAI o1/o3）
                            reasoning_str = delta.get("reasoning_content")
                            if reasoning_str:
                                reasoning_parts.append(reasoning_str)
                            reasoning_details = delta.get("reasoning_details")
                            if reasoning_details:
                                for detail in reasoning_details:
                                    if isinstance(detail, dict) and detail.get("text"):
                                        reasoning_parts.append(detail["text"])

                            # Tool calls（流式累积）
                            for tc in delta.get("tool_calls", []):
                                idx = _resolve_tool_call_index(tc, pending_calls)
                                if idx not in pending_calls:
                                    pending_calls[idx] = {
                                        "id": tc.get("id", f"call_{uuid4().hex[:12]}"),
                                        "name": tc.get("function", {}).get("name", ""),
                                        "parts": [],
                                    }
                                    yield ToolUseStartEvent(
                                        tool_use_id=pending_calls[idx]["id"],
                                        tool_name=pending_calls[idx]["name"],
                                    )
                                else:
                                    if tc.get("id"):
                                        pending_calls[idx]["id"] = tc["id"]
                                    fname = tc.get("function", {}).get("name", "")
                                    if fname:
                                        pending_calls[idx]["name"] = fname

                                fragment = tc.get("function", {}).get("arguments", "")
                                if fragment:
                                    pending_calls[idx]["parts"].append(fragment)
                                    yield ToolUseDeltaEvent(
                                        tool_use_id=pending_calls[idx]["id"],
                                        json_fragment=fragment,
                                    )

                    # ── 流结束：发出 ToolUseEnd ──
                    for call in pending_calls.values():
                        full_json = "".join(call["parts"])
                        try:
                            args = json.loads(full_json) if full_json else {}
                        except json.JSONDecodeError:
                            args = {"_raw": full_json}
                        yield ToolUseEndEvent(
                            tool_use_id=call["id"],
                            tool_name=call["name"],
                            arguments=args,
                        )

                    # ── Reasoning 汇总 ──
                    reasoning_text = "".join(reasoning_parts)
                    # Fallback: <think> tag extraction
                    if not reasoning_text and caps and caps.reasoning_format == "think_tags":
                        reasoning_text = _extract_think_tags("".join(assistant_text_parts))

                    yield DoneEvent(
                        stop_reason=stop_reason,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        reasoning_content=reasoning_text or None,
                        reasoning_tokens=reasoning_tokens,
                        cached_tokens=cached_tokens,
                        model=actual_model,
                    )

        except httpx.TimeoutException as exc:
            yield ErrorEvent(message=f"Request timed out: {exc}", code="timeout")
        except httpx.RequestError as exc:
            yield ErrorEvent(message=f"Request error: {exc}", code="request_error")

    async def list_models(self) -> list[ModelInfo]:
        """获取可用模型列表"""
        try:
            async with httpx.AsyncClient(timeout=10.0, proxy=self._proxy) as client:
                resp = await client.get(
                    self._api_url("/v1/models"),
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                return [
                    ModelInfo(
                        provider=self._provider_kind,
                        model_id=m.get("id", ""),
                        display_name=m.get("id", ""),
                    )
                    for m in data.get("data", [])
                    if m.get("id")
                ]
        except Exception:
            return []
