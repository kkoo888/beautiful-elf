"""知识库模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Index
from app.models.base import BaseModel


class KnowledgeDocument(BaseModel):
    __tablename__ = "knowledge_document"

    filename = Column(String(512), nullable=False, comment="文件名")
    file_type = Column(String(32), nullable=False, comment="文件类型")
    file_size = Column(BigInteger, nullable=False, default=0, comment="文件大小 (字节)")
    chunk_count = Column(Integer, nullable=False, default=0, comment="分块数量")
    status = Column(Integer, nullable=False, default=0, comment="处理状态 (0=待处理, 1=处理中, 2=完成, 3=失败)")
    error_message = Column(String(1024), default="", comment="失败原因")

    __table_args__ = (
        Index("idx_knowledge_document_file_type", "file_type"),
        Index("idx_knowledge_document_status", "status"),
        Index("idx_knowledge_document_is_deleted", "is_deleted"),
    )


class KnowledgeChunk(BaseModel):
    __tablename__ = "knowledge_chunk"

    document_id = Column(BigInteger, nullable=False, comment="文档 ID")
    chunk_index = Column(Integer, nullable=False, comment="分块序号")
    content_preview = Column(String(512), default="", comment="内容预览")
    qdrant_point_id = Column(String(128), nullable=False, comment="Qdrant 向量 ID")

    __table_args__ = (
        Index("idx_knowledge_chunk_document_index", "document_id", "chunk_index"),
        Index("idx_knowledge_chunk_qdrant_point", "qdrant_point_id"),
    )
