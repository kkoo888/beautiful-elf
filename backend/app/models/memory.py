"""长期记忆模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, JSON, DateTime, Numeric, Index
from app.models.base import BaseModel


class MemoryEntry(BaseModel):
    __tablename__ = "memory_entry"

    conversation_id = Column(BigInteger, nullable=False, default=0, comment="来源会话 ID (0=无关联)")
    content = Column(Text, nullable=False, default="", comment="原始对话内容")
    summary = Column(Text, nullable=False, comment="记忆摘要")
    tags = Column(JSON, nullable=False, default=list, comment="标签列表")
    importance = Column(Integer, nullable=False, default=5, comment="重要度 (1-10)")
    qdrant_point_id = Column(String(128), nullable=False, default="", comment="Qdrant 向量 ID")

    # v5.0: 认知衰减字段（ACT-R 激活度模型）
    activation = Column(Numeric(6, 4), nullable=False, default=1.0, comment="持久化激活度 [0,1]")
    access_count = Column(BigInteger, nullable=False, default=0, comment="被检索命中次数")
    last_accessed_at = Column(DateTime, nullable=False, default="1970-01-01 00:00:00", comment="最后被访问时间")
    decay_status = Column(String(16), nullable=False, default="active", comment="active/dormant/archived")

    __table_args__ = (
        Index("idx_memory_entry_conversation", "conversation_id"),
        Index("idx_memory_entry_importance", "importance"),
        Index("idx_memory_entry_is_deleted", "is_deleted"),
        Index("idx_memory_entry_activation", "activation"),
        Index("idx_memory_entry_decay_status", "decay_status"),
    )
