"""LLM 服务工厂 — 统一多供应商接入，Agent 和 RAG 共用

架构:
  MySQL llm_provider 表 → LLMService（运行时） → LangChain / LlamaIndex 兼容实例
  Agent 引擎、RAG 查询改写、摘要压缩等全部通过此服务获取 LLM

设计原则:
  - 从 DB 读取供应商配置，支持热更新
  - 返回 LangChain 兼容的 ChatModel（支持 Tool Calling）
  - 返回 LlamaIndex 兼容的 Embedding / LLM（用于 RAG）
  - httpx 连接池复用（不每次请求新建）
"""
from typing import Optional, Dict, Any, List
import logging
import time

from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    LLM 服务 — 根据 DB 配置创建 LangChain/LlamaIndex 兼容实例。

    使用方式:
        llm_service = LLMService()
        llm = await llm_service.get_chat_llm(db, provider_id=1, model_name="qwen3.5:7b")
        response = await llm.ainvoke([HumanMessage(content="你好")])
    """

    # [P2] 缓存 TTL（秒）— 供应商配置变更后最多 5 分钟自动失效
    _CACHE_TTL = 300

    def __init__(self):
        self._cache: Dict[str, Any] = {}        # cache_key → llm instance
        self._cache_ts: Dict[str, float] = {}   # cache_key → 创建时间戳

    async def get_chat_llm(
        self,
        db,
        provider_id: int,
        model_name: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        bind_tools: list = None,
    ):
        """
        获取 LangChain ChatModel 实例（支持 Tool Calling）。

        Args:
            db: 数据库会话
            provider_id: 供应商 ID（从 MySQL llm_provider 表读取）
            model_name: 模型名称（为空时用供应商默认模型）
            temperature: 温度
            max_tokens: 最大 token
            bind_tools: LangChain Tool 列表（可选，绑定后支持 Tool Calling）

        Returns:
            LangChain BaseChatModel 实例
        """
        from app.services.llm_provider_service import LLMProviderService
        from app.repository.llm_provider_repo import LLMProviderRepository
        from app.repository.llm_model_repo import LLMModelRepository
        provider_repo = LLMProviderRepository()
        model_repo = LLMModelRepository()
        # 直接读 ORM 模型，避免 ProviderOut 脱敏 api_key
        provider = await provider_repo.find_by_id(db, provider_id)

        if not provider:
            raise ValueError(f"供应商 ID={provider_id} 不存在")

        # 确定模型名 — 从 llm_model 表查询（方案 A: 两表分离）
        if not model_name:
            models = await model_repo.find_enabled_by_provider(db, provider_id)
            model_name = models[0].model_name if models else ""

        if not model_name:
            raise ValueError(f"供应商 '{provider.name}' 未配置模型")

        cache_key = f"{provider_id}:{model_name}:{temperature}"
        llm = self._cache.get(cache_key)
        cached_ts = self._cache_ts.get(cache_key, 0)

        # [P2] TTL 检查：缓存超过 _CACHE_TTL 秒自动失效
        if llm is not None and (time.time() - cached_ts) > self._CACHE_TTL:
            logger.info(f"[llm_service] 缓存过期({cache_key})，重新创建")
            llm = None

        if llm is not None:
            pass  # 命中缓存
        else:
            llm = self._create_langchain_llm(
                provider_type=provider.provider_type,
                base_url=provider.base_url,
                api_key=getattr(provider, "api_key", "") or "",
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._cache[cache_key] = llm
            self._cache_ts[cache_key] = time.time()

        # 绑定工具
        if bind_tools:
            return llm.bind_tools(bind_tools)

        return llm

    def _create_langchain_llm(
        self,
        provider_type: str,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ):
        """根据供应商类型创建 LangChain ChatModel"""
        provider_type = provider_type.lower()

        if provider_type == "ollama":
            return self._create_ollama_llm(base_url, model, temperature, max_tokens)
        elif provider_type in ("openai", "deepseek", "qwen", "agnes", "custom"):
            return self._create_openai_compat_llm(
                base_url, api_key, model, temperature, max_tokens
            )
        else:
            raise ValueError(f"不支持的供应商类型: {provider_type}")

    def _create_ollama_llm(
        self, base_url: str, model: str, temperature: float, max_tokens: int
    ):
        """创建 Ollama ChatModel"""
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model,
                base_url=base_url,
                temperature=temperature,
                num_predict=max_tokens,
            )
        except ImportError:
            raise ImportError(
                "缺少 langchain-ollama，请执行: pip install langchain-ollama"
            )

    def _create_openai_compat_llm(
        self, base_url: str, api_key: str, model: str,
        temperature: float, max_tokens: int,
    ):
        """创建 OpenAI 兼容 ChatModel（DeepSeek/Kimi/硅基流动等）"""
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model,
                base_url=base_url.rstrip("/"),
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ImportError:
            raise ImportError(
                "缺少 langchain-openai，请执行: pip install langchain-openai"
            )

    def clear_cache(self):
        """清空 LLM 缓存（供应商配置变更时调用）"""
        self._cache.clear()
        self._cache_ts.clear()
        logger.info("LLM 缓存已清空")


# ── 全局单例 ──────────────────────────────────────────────

llm_service = LLMService()
