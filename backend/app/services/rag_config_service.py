"""RAG 配置 Service — 业务编排 + 事务管理"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repository.rag_config_repo import RagConfigRepository


class RagConfigService:

    def __init__(self):
        self.repo = RagConfigRepository()

    # 默认配置（DB 无记录时返回）
    DEFAULTS = {
        "chunk_size": 2048, "chunk_overlap": 256,
        "similarity_top_k": 10, "bm25_top_n": 20, "rrf_k": 60,
        "rerank_enabled": 1, "rerank_top_n": 5,
        "embedding_model": "", "embedding_dimension": 1024,
        "query_rewrite_enabled": 1,
    }

    async def get_config(self, db: AsyncSession) -> dict:
        """获取 RAG 配置（DB 无记录时返回默认值）"""
        config = await self.repo.get(db)
        if not config:
            return self._defaults()
        return self._to_dict(config)

    @classmethod
    def _defaults(cls) -> dict:
        """返回默认配置 dict"""
        return {
            "id": 1,
            "chunkSize": cls.DEFAULTS["chunk_size"],
            "chunkOverlap": cls.DEFAULTS["chunk_overlap"],
            "similarityTopK": cls.DEFAULTS["similarity_top_k"],
            "bm25TopN": cls.DEFAULTS["bm25_top_n"],
            "rrfK": cls.DEFAULTS["rrf_k"],
            "rerankEnabled": cls.DEFAULTS["rerank_enabled"] == 1,
            "rerankTopN": cls.DEFAULTS["rerank_top_n"],
            "embeddingModel": cls.DEFAULTS["embedding_model"],
            "embeddingDimension": cls.DEFAULTS["embedding_dimension"],
            "queryRewriteEnabled": cls.DEFAULTS["query_rewrite_enabled"] == 1,
            "createdAt": None,
            "updatedAt": None,
        }

    async def update_config(self, db: AsyncSession, data: dict) -> dict:
        """更新 RAG 配置"""
        # 参数校验
        validated = self._validate(data)
        config = await self.repo.create_or_update(db, validated)
        await db.commit()
        return self._to_dict(config)

    @staticmethod
    def _validate(data: dict) -> dict:
        """参数校验"""
        validated = {}
        int_fields = {
            "chunk_size": (128, 8192),
            "chunk_overlap": (0, 2048),
            "similarity_top_k": (1, 50),
            "bm25_top_n": (1, 100),
            "rrf_k": (1, 200),
            "rerank_top_n": (1, 20),
            "embedding_dimension": (64, 4096),
        }
        bool_fields = ["rerank_enabled", "query_rewrite_enabled"]
        str_fields = ["embedding_model"]

        for field, (min_val, max_val) in int_fields.items():
            if field in data and data[field] is not None:
                validated[field] = max(min_val, min(max_val, int(data[field])))

        for field in bool_fields:
            if field in data and data[field] is not None:
                validated[field] = 1 if data[field] else 0

        for field in str_fields:
            if field in data:
                validated[field] = str(data[field])[:128]

        return validated

    @staticmethod
    def _to_dict(config) -> dict:
        """模型 → dict"""
        return {
            "id": config.id,
            "chunkSize": config.chunk_size,
            "chunkOverlap": config.chunk_overlap,
            "similarityTopK": config.similarity_top_k,
            "bm25TopN": config.bm25_top_n,
            "rrfK": config.rrf_k,
            "rerankEnabled": config.rerank_enabled == 1,
            "rerankTopN": config.rerank_top_n,
            "embeddingModel": config.embedding_model,
            "embeddingDimension": config.embedding_dimension,
            "queryRewriteEnabled": config.query_rewrite_enabled == 1,
            "createdAt": config.created_at.isoformat() if config.created_at else None,
            "updatedAt": config.updated_at.isoformat() if config.updated_at else None,
        }


rag_config_service = RagConfigService()
