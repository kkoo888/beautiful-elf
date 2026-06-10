"""LLM 服务工厂 — 统一多供应商接入

v5.0 架构:
  MySQL llm_provider 表 → LLMRuntime → ChatLLMProvider (适配器) → LangChain/LangGraph

所有 LLM 调用都走 LLMProvider.chat()，输出统一为 StreamEvent。
LangChain 只是 Agent 图的适配层，不再是 LLM 调用层。
"""
from typing import Optional, Dict, Any
import logging
import time

from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    LLM 服务 — 从 DB 配置构建 LangChain 兼容的 ChatModel。

    v5.0: 底层统一走 LLMProvider，LangChain 通过 ChatLLMProvider 适配器接入。

    使用方式:
        llm_service = LLMService()
        llm = await llm_service.get_chat_llm(db, provider_id=1, model_name="deepseek-chat")
        response = await llm.ainvoke([HumanMessage(content="你好")])
    """

    # 缓存 TTL（秒）
    _CACHE_TTL = 300

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ts: Dict[str, float] = {}

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
        获取 LangChain ChatModel 实例。

        v5.0: 返回 ChatLLMProvider 适配器（内部走 LLMProvider）。

        Args:
            db: 数据库会话
            provider_id: 供应商 ID
            model_name: 模型名称（为空时用供应商默认模型）
            temperature: 温度
            max_tokens: 最大 token
            bind_tools: LangChain Tool 列表（可选）

        Returns:
            LangChain BaseChatModel 实例（ChatLLMProvider）
        """
        from app.repository.llm_provider_repo import LLMProviderRepository
        from app.repository.llm_model_repo import LLMModelRepository
        from app.llm.runtime import llm_runtime
        from app.llm.langchain_adapter import ChatLLMProvider

        provider_repo = LLMProviderRepository()
        model_repo = LLMModelRepository()

        provider = await provider_repo.find_by_id(db, provider_id)
        if not provider:
            raise ValueError(f"供应商 ID={provider_id} 不存在")

        # 确定模型名
        if not model_name:
            models = await model_repo.find_enabled_by_provider(db, provider_id)
            model_name = models[0].model_name if models else ""

        if not model_name:
            raise ValueError(f"供应商 '{provider.name}' 未配置模型")

        # 缓存检查
        cache_key = f"{provider_id}:{model_name}:{temperature}"
        llm = self._cache.get(cache_key)
        cached_ts = self._cache_ts.get(cache_key, 0)

        if llm is not None and (time.time() - cached_ts) > self._CACHE_TTL:
            logger.info(f"[llm_service] 缓存过期({cache_key})，重新创建")
            llm = None

        if llm is None:
            # 从 DB 构建 LLMProvider 运行时
            llm_provider = llm_runtime.from_db_provider(provider, model_name)

            # 包装成 LangChain 兼容的 ChatModel
            llm = ChatLLMProvider(
                provider=llm_provider,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._cache[cache_key] = llm
            self._cache_ts[cache_key] = time.time()

        # 绑定工具
        if bind_tools:
            return llm.bind_tools(bind_tools)

        return llm

    def clear_cache(self):
        """清空 LLM 缓存（供应商配置变更时调用）"""
        self._cache.clear()
        self._cache_ts.clear()
        logger.info("LLM 缓存已清空")


# ── 全局单例 ──────────────────────────────────────────────

llm_service = LLMService()
