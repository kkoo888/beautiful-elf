"""长期记忆模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, JSON, Index
from app.models.base import BaseModel


class MemoryEntry(BaseModel):
    __tablename__ = "memory_entry"

    conversation_id = Column(BigInteger, default=None, comment="来源会话 ID")
    summary = Column(Text, nullable=False, comment="记忆摘要")
    tags = Column(JSON, default=None, comment="标签列表")
    importance = Column(Integer, nullable=False, default=5, comment="重要度 (1-10)")
    qdrant_point_id = Column(String(128), default=None, comment="Qdrant 向量 ID")

    __table_args__ = (
        Index("idx_memory_entry_conversation", "conversation_id"),
        Index("idx_memory_entry_importance", "importance"),
        Index("idx_memory_entry_is_deleted", "is_deleted"),
    )
