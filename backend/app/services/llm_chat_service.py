"""统一 LLM 对话服务 — 支持 OpenAI 兼容 + Ollama + Claude"""

import json
import logging
from typing import List, Optional, AsyncIterator
import httpx

from app.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)

# OpenAI 兼容供应商类型（使用 /v1/chat/completions）
OPENAI_COMPAT_TYPES = {"openai", "deepseek", "qwen", "custom"}


class LLMChatService:
    """统一 LLM 对话服务"""

    def __init__(self):
        self.provider_service = LLMProviderService()

    async def chat(
        self,
        db,
        provider_id: int,
        model_name: str,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict:
        """非流式对话

        Returns:
            {"content": "...", "model": "...", "provider_type": "...", "token_count": 123}
        """
        provider = await self.provider_service.get(db, provider_id)
        provider_type = provider.provider_type

        if provider_type in OPENAI_COMPAT_TYPES:
            return await self._chat_openai_compat(
                provider, model_name, messages, temperature, max_tokens
            )
        elif provider_type == "ollama":
            return await self._chat_ollama(
                provider, model_name, messages, temperature, max_tokens
            )
        else:
            raise ValueError(f"不支持的供应商类型: {provider_type}")

    async def chat_stream(
        self,
        db,
        provider_id: int,
        model_name: str,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """流式对话，逐 token 返回"""
        provider = await self.provider_service.get(db, provider_id)
        provider_type = provider.provider_type

        if provider_type in OPENAI_COMPAT_TYPES:
            async for chunk in self._stream_openai_compat(
                provider, model_name, messages, temperature, max_tokens
            ):
                yield chunk
        elif provider_type == "ollama":
            async for chunk in self._stream_ollama(
                provider, model_name, messages, temperature, max_tokens
            ):
                yield chunk
        else:
            raise ValueError(f"不支持的供应商类型: {provider_type}")

    # ── OpenAI 兼容接口 ──────────────────────────────────────

    async def _chat_openai_compat(
        self, provider, model: str, messages: List[dict],
        temperature: float, max_tokens: int,
    ) -> dict:
        base_url = provider.base_url.rstrip("/")
        api_key = getattr(provider, "api_key", "") or ""

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})

            return {
                "content": content,
                "model": data.get("model", model),
                "provider_type": provider.provider_type,
                "token_count": usage.get("total_tokens", 0),
            }

    async def _stream_openai_compat(
        self, provider, model: str, messages: List[dict],
        temperature: float, max_tokens: int,
    ) -> AsyncIterator[str]:
        base_url = provider.base_url.rstrip("/")
        api_key = getattr(provider, "api_key", "") or ""

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    # ── Ollama 接口 ──────────────────────────────────────────

    async def _chat_ollama(
        self, provider, model: str, messages: List[dict],
        temperature: float, max_tokens: int,
    ) -> dict:
        base_url = provider.base_url.rstrip("/")

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

            return {
                "content": data.get("message", {}).get("content", ""),
                "model": data.get("model", model),
                "provider_type": "ollama",
                "token_count": data.get("eval_count", 0),
            }

    async def _stream_ollama(
        self, provider, model: str, messages: List[dict],
        temperature: float, max_tokens: int,
    ) -> AsyncIterator[str]:
        base_url = provider.base_url.rstrip("/")

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
