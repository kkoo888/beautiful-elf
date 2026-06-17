"""Ollama LLM 服务 — 从 MySQL settings 表读取配置，调用 Ollama API

settings 表中的配置键:
  - ollama.host        → Ollama 服务地址 (如 http://localhost:11434)
  - ollama.chat_model  → 对话模型名称 (如 qwen3.5:7b)
  - ollama.embed_model → 嵌入模型名称 (如 qwen3-embedding:latest)
  - ollama.temperature → 全局温度 (可选, 默认 0.7)
  - ollama.max_tokens  → 全局最大 token (可选, 默认 2048)
"""
import json
import logging
from typing import Optional, List, AsyncIterator
import httpx

logger = logging.getLogger(__name__)

# 模块级配置缓存，避免每次都查数据库
_config_cache: dict = {}


async def load_ollama_config(db) -> None:
    """从 settings 表加载 Ollama 配置到内存缓存（启动时调用）"""
    from app.repository.config_repo import ConfigRepository

    repo = ConfigRepository()
    keys = ["ollama.host", "ollama.chat_model", "ollama.embed_model", "ollama.temperature", "ollama.max_tokens"]
    for key in keys:
        setting = await repo.find_by_key(db, key)
        if setting:
            try:
                _config_cache[key] = json.loads(setting.key_value)
            except (json.JSONDecodeError, TypeError):
                _config_cache[key] = setting.key_value
        else:
            # 使用默认值
            defaults = {
                "ollama.host": "http://localhost:11434",
                "ollama.chat_model": "qwen3.5:0.8b",
                "ollama.embed_model": "qwen3-embedding:latest",
                "ollama.temperature": 0.7,
                "ollama.max_tokens": 2048,
            }
            _config_cache[key] = defaults.get(key)

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
