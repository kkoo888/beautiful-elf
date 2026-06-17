"""Ollama LLM 服务 — 从 llm_provider / llm_model 表读取配置，调用 Ollama API

配置来源（统一从供应商表读取）:
  - llm_provider.base_url  → Ollama 服务地址
  - llm_model.model_name   → 对话/嵌入模型名称
  - llm_model.temperature  → 温度
  - llm_model.max_tokens   → 最大 token
"""
import json
import logging
from typing import Optional, List, AsyncIterator
import httpx

logger = logging.getLogger(__name__)

# 模块级配置缓存，避免每次都查数据库
_config_cache: dict = {}


async def load_ollama_config(db) -> None:
    """从 llm_provider / llm_model 表加载 Ollama 配置到内存缓存（启动时调用）"""
    from app.repository.llm_provider_repo import LLMProviderRepository
    from app.repository.llm_model_repo import LLMModelRepository

    provider_repo = LLMProviderRepository()
    model_repo = LLMModelRepository()

    # 查找 Ollama 供应商
    provider = await provider_repo.find_by_type(db, "ollama")
    if provider:
        _config_cache["ollama.host"] = provider.base_url.rstrip("/")
    else:
        _config_cache["ollama.host"] = "http://localhost:11434"

    # 查找 Ollama 下的模型
    if provider:
        models = await model_repo.find_by_provider(db, provider.id)
        enabled_models = [m for m in models if m.is_enabled == 1]

        # 对话模型：优先取非 embedding 模型
        chat_models = [m for m in enabled_models if "embed" not in m.model_name.lower()]
        if chat_models:
            _config_cache["ollama.chat_model"] = chat_models[0].model_name
            _config_cache["ollama.temperature"] = chat_models[0].temperature
            _config_cache["ollama.max_tokens"] = chat_models[0].max_tokens

        # 嵌入模型
        embed_models = [m for m in enabled_models if "embed" in m.model_name.lower()]
        if embed_models:
            _config_cache["ollama.embed_model"] = embed_models[0].model_name

    # 兜底默认值
    _config_cache.setdefault("ollama.chat_model", "qwen3.5:0.8b")
    _config_cache.setdefault("ollama.embed_model", "qwen3-embedding:latest")
    _config_cache.setdefault("ollama.temperature", 0.7)
    _config_cache.setdefault("ollama.max_tokens", 2048)

    logger.info(f"Ollama 配置已加载: host={get_host()}, chat_model={get_chat_model()}")


def get_host() -> str:
    """获取 Ollama 服务地址"""
    return _config_cache.get("ollama.host", "http://localhost:11434")


def get_chat_model() -> str:
    """获取对话模型名称"""
    return _config_cache.get("ollama.chat_model", "qwen3.5:0.8b")


def get_embed_model() -> str:
    """获取嵌入模型名称"""
    return _config_cache.get("ollama.embed_model", "qwen3-embedding:latest")


def get_temperature() -> float:
    """获取全局温度"""
    val = _config_cache.get("ollama.temperature", 0.7)
    return float(val) if val is not None else 0.7


def get_max_tokens() -> int:
    """获取全局最大 token"""
    val = _config_cache.get("ollama.max_tokens", 2048)
    return int(val) if val is not None else 2048


def update_config_cache(key: str, value) -> None:
    """运行时更新配置缓存（当用户修改 settings 时调用）"""
    _config_cache[key] = value


# ── 模块级共享 httpx 客户端（连接池复用） ──────────────────
_shared_client: Optional[httpx.AsyncClient] = None


def _get_shared_client() -> httpx.AsyncClient:
    """获取模块级共享 httpx 客户端，所有 OllamaClient 实例复用同一连接池"""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _shared_client


async def close_ollama_client() -> None:
    """关闭共享 httpx 客户端（应用关闭时调用）"""
    global _shared_client
    if _shared_client and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None


class OllamaClient:
    """Ollama API 客户端 — 封装 HTTP 调用，复用模块级连接池"""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = (host or get_host()).rstrip("/")
        self.model = model or get_chat_model()

    async def chat(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> dict:
        """调用 Ollama Chat API (非流式)

        Args:
            messages: 消息列表 [{"role": "system"|"user"|"assistant", "content": "..."}]
            temperature: 温度 (覆盖全局配置)
            max_tokens: 最大 token (覆盖全局配置)
            model: 模型名称 (覆盖全局配置)

        Returns:
            {"content": "回复内容", "model": "使用的模型", "total_duration": 耗时ns, "eval_count": token数}
        """
        use_model = model or self.model
        use_temp = temperature if temperature is not None else get_temperature()
        use_max = max_tokens or get_max_tokens()

        payload = {
            "model": use_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": use_temp,
                "num_predict": use_max,
            },
        }

        client = _get_shared_client()
        try:
            resp = await client.post(f"{self.host}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

            return {
                "content": data.get("message", {}).get("content", ""),
                "model": data.get("model", use_model),
                "total_duration": data.get("total_duration", 0),
                "eval_count": data.get("eval_count", 0),
            }
        except httpx.TimeoutException:
            logger.error(f"Ollama 调用超时: model={use_model}")
            raise RuntimeError(f"Ollama 模型 {use_model} 响应超时，请检查服务状态")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP 错误: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"Ollama 返回错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Ollama 调用异常: {e}")
            raise RuntimeError(f"Ollama 调用失败: {e}")

    async def chat_stream(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """调用 Ollama Chat API (流式)"""
        use_model = model or self.model
        use_temp = temperature if temperature is not None else get_temperature()
        use_max = max_tokens or get_max_tokens()

        payload = {
            "model": use_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": use_temp,
                "num_predict": use_max,
            },
        }

        client = _get_shared_client()
        try:
            async with client.stream("POST", f"{self.host}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Ollama 流式调用异常: {e}")
            raise RuntimeError(f"Ollama 流式调用失败: {e}")

    async def embeddings(self, text: str, model: Optional[str] = None) -> List[float]:
        """调用 Ollama Embeddings API"""
        use_model = model or get_embed_model()

        client = _get_shared_client()
        try:
            resp = await client.post(
                f"{self.host}/api/embeddings",
                json={"model": use_model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Ollama Embedding 调用异常: {e}")
            raise RuntimeError(f"Ollama Embedding 失败: {e}")

    async def health_check(self) -> dict:
        """检查 Ollama 服务状态"""
        try:
            client = _get_shared_client()
            resp = await client.get(f"{self.host}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"status": "ok", "models": models, "host": self.host}
        except Exception as e:
            return {"status": "error", "message": str(e), "host": self.host}
