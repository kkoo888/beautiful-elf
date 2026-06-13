"""AI 反馈模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, JSON, Index
from app.models.base import BaseModel


class AIFeedback(BaseModel):
    __tablename__ = "ai_feedback"

    conversation_id = Column(BigInteger, nullable=False, default=0, comment="会话 ID (0=无关联)")
    question = Column(Text, nullable=False, comment="用户问题")
    answer = Column(Text, nullable=False, comment="AI 回答")
    feedback_type = Column(Integer, nullable=False, comment="反馈类型")
    reason_tags = Column(JSON, nullable=False, default=list, comment="原因标签")
    reason_text = Column(String(2048), nullable=False, default="", comment="自由文本")
    trace_id = Column(String(128), nullable=False, default="", comment="请求链路 ID")

    __table_args__ = (
        Index("idx_ai_feedback_type", "feedback_type"),
        Index("idx_ai_feedback_conversation", "conversation_id"),
        Index("idx_ai_feedback_created_at", "created_at"),
    )
