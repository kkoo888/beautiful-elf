"""知识库 Schema — 统一 CamelModel"""
from typing import List, Optional
from pydantic import Field
from app.schemas.base import CamelModel


class KnowledgeDocumentOut(CamelModel):
    """知识库文档响应"""
    id: int = Field(..., description="文档 ID")
    filename: str = Field(default="", description="文件名")
    file_type: str = Field(default="", description="文件类型")
    file_size: int = Field(default=0, description="文件大小 (字节)")
    chunk_count: int = Field(default=0, description="分块数量")
    status: int = Field(default=0, description="处理状态 (0=待处理, 1=处理中, 2=完成, 3=失败)")
    error_message: str = Field(default="", description="失败原因")


class KnowledgeChunkOut(CamelModel):
    """知识库分块响应"""
    id: int = Field(..., description="分块 ID")
    document_id: int = Field(..., description="文档 ID")
    chunk_index: int = Field(..., description="分块序号")
    content_preview: str = Field(default="", description="内容预览")


class KnowledgeSearchResult(CamelModel):
    """语义搜索结果"""
    document_id: int = Field(default=0, description="文档 ID")
    filename: str = Field(default="", description="文件名")
    content: str = Field(default="", description="匹配内容")
    score: float = Field(default=0.0, description="相关度分数")


class KnowledgeSearchResponse(CamelModel):
    """语义搜索响应"""
    items: List[KnowledgeSearchResult] = Field(default_factory=list, description="搜索结果")
    total: int = Field(default=0, description="结果总数")


# ── Qdrant 管理响应 ───────────────────────────────────────


class QdrantCollectionStats(CamelModel):
    """Qdrant 集合状态"""
    collection_name: str = Field(default="", description="集合名称")
    vector_count: int = Field(default=0, description="向量总数")
    status: str = Field(default="unknown", description="集合状态 (green/yellow/red)")
    is_connected: bool = Field(default=False, description="是否连接正常")


class DocumentVectorCount(CamelModel):
    """按文档聚合的向量计数"""
    document_id: int = Field(..., description="文档 ID")
    filename: str = Field(default="", description="文件名")
    vector_count: int = Field(default=0, description="Qdrant 中的向量数")


class QdrantVectorRecord(CamelModel):
    """Qdrant 单条向量记录"""
    point_id: str = Field(..., description="向量 ID")
    chunk_id: str = Field(default="", description="分块 ID")
    filename: str = Field(default="", description="来源文件名")
    content_preview: str = Field(default="", description="内容预览")
