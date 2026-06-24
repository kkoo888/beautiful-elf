"""Embeddings 适配层 — LangChain Embeddings 接口包装 ONNX 本地模型

提供 get_embeddings() 返回 LangChain 兼容的 Embeddings 对象，
供 expert_team memory/knowledge 模块使用。
"""
from typing import List, Optional

from langchain_core.embeddings import Embeddings

from app.core.logging import get_logger

logger = get_logger(__name__)


class OnnxLangchainEmbedding(Embeddings):
    """LangChain Embeddings 接口 — 委托给 OnnxEmbeddingService"""

    def __init__(self):
        self._service = None

    async def _ensure_service(self):
        if self._service is None:
            from app.services.onnx_embedding_service import get_onnx_embedding_service
            self._service = await get_onnx_embedding_service()
        return self._service

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        service = await self._ensure_service()
        return await service.get_embeddings(texts)

    async def aembed_query(self, text: str) -> List[float]:
        service = await self._ensure_service()
        return await service.get_embedding(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.aembed_documents(texts)).result()
        return asyncio.run(self.aembed_documents(texts))

    def embed_query(self, text: str) -> List[float]:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.aembed_query(text)).result()
        return asyncio.run(self.aembed_query(text))


_instance: Optional[OnnxLangchainEmbedding] = None


def get_embeddings() -> OnnxLangchainEmbedding:
    """获取全局 LangChain Embeddings 单例"""
    global _instance
    if _instance is None:
        _instance = OnnxLangchainEmbedding()
    return _instance
