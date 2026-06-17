"""Qdrant 向量数据库客户端 - 独立封装"""
from qdrant_client import QdrantClient
from app.core.config import get_settings

settings = get_settings()

qdrant_client = QdrantClient(
    url=settings.QDRANT_URL,
    timeout=30,
    trust_env=False,
)


def get_qdrant() -> QdrantClient:
    """获取 Qdrant 客户端（FastAPI 依赖注入用）"""
    return qdrant_client
