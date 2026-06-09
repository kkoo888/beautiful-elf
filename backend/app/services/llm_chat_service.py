"""统一 LLM 对话服务 — 支持 OpenAI 兼容 + Ollama

供 skill_executor 调用（非流式直接 LLM 调用）。
对话主路径走 agent_service → LangGraph，不经过本服务。
"""
import logging
from typing import List
import httpx

from app.schemas.chat import ChatResponse
from app.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)

# OpenAI 兼容供应商类型（使用 /v1/chat/completions）
OPENAI_COMPAT_TYPES = {"openai", "deepseek", "qwen", "custom"}


class LLMChatService:
    """统一 LLM 对话服务（供 skill_executor 使用）"""

    def __init__(self):
        self.provider_service = LLMProviderService()
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """获取 httpx 客户端（连接池复用）"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(max_connections=30, max_keepalive_connections=15),
            )
        return self._client

    async def close(self):
        """关闭连接池"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def chat(
        self,
        db,
        provider_id: int,
        model_name: str,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResponse:
        """非流式对话（skill_executor 使用）"""
        provider = await self.provider_service.get_provider(db, provider_id)
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

    # ── OpenAI 兼容接口 ──────────────────────────────────────

    async def _chat_openai_compat(
        self, provider, model: str, messages: List[dict],
        temperature: float, max_tokens: int,
    ) -> ChatResponse:
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

        client = self._get_client()
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

        return ChatResponse(
            content=content,
            model=data.get("model", model),
            provider_type=provider.provider_type,
            token_count=usage.get("total_tokens", 0),
        )

    # ── Ollama 接口 ──────────────────────────────────────────

    async def _chat_ollama(
        self, provider, model: str, messages: List[dict],
        temperature: float, max_tokens: int,
    ) -> ChatResponse:
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

        client = self._get_client()
        resp = await client.post(f"{base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        return ChatResponse(
            content=data.get("message", {}).get("content", ""),
            model=data.get("model", model),
            provider_type="ollama",
            token_count=data.get("eval_count", 0),
        )
