"""RAG 检索配置模型 — 管理分块、检索、重排序等参数"""
from sqlalchemy import Column, Integer, String, SmallInteger
from app.models.base import BaseModel


class RagConfig(BaseModel):
    """RAG 检索配置（单例模式，只有一条记录）"""
    __tablename__ = "rag_config"

    # ── 分块参数 ──
    chunk_size = Column(Integer, nullable=False, server_default="2048", comment="分块大小（tokens）")
    chunk_overlap = Column(Integer, nullable=False, server_default="256", comment="分块重叠（tokens）")

    # ── 检索参数 ──
    similarity_top_k = Column(Integer, nullable=False, server_default="10", comment="向量检索返回条数")
    bm25_top_n = Column(Integer, nullable=False, server_default="20", comment="BM25 检索返回条数")
    rrf_k = Column(Integer, nullable=False, server_default="60", comment="RRF 融合参数 k")

    # ── 重排序参数 ──
    rerank_enabled = Column(SmallInteger, nullable=False, server_default="1", comment="是否启用重排序: 1=启用 0=禁用")
    rerank_top_n = Column(Integer, nullable=False, server_default="5", comment="重排序后保留条数")

    # ── Embedding 参数 ──
    embedding_model = Column(String(128), nullable=False, server_default="", comment="Embedding 模型名称")
    embedding_dimension = Column(Integer, nullable=False, server_default="1024", comment="Embedding 向量维度")

    # ── 查询改写参数 ──
    query_rewrite_enabled = Column(SmallInteger, nullable=False, server_default="1", comment="是否启用查询改写")
