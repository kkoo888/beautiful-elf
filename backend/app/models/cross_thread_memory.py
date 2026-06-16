"""跨线程记忆模型"""
from sqlalchemy import Column, BigInteger, Integer, String, JSON, Index
from app.models.base import BaseModel


class CrossThreadMemory(BaseModel):
    __tablename__ = "cross_thread_memory"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    namespace = Column(String(100), nullable=False, default="conversations", comment="命名空间")
    memory_key = Column(String(100), nullable=False, default="", comment="记忆唯一标识")
    content = Column(JSON, nullable=False, default=dict, comment="记忆内容")

    __table_args__ = (
        Index("idx_user_namespace", "user_id", "namespace"),
        Index("idx_key", "memory_key"),
    )
