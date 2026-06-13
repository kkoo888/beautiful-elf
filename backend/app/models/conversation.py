"""会话 & 消息模型"""
from datetime import datetime

from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, JSON, Index
from app.models.base import BaseModel


class Conversation(BaseModel):
    __tablename__ = "conversation"

    title = Column(String(256), nullable=False, default="", comment="会话标题")
    model_name = Column(String(128), nullable=False, default="", comment="对话模型")
    message_count = Column(Integer, nullable=False, default=0, comment="消息数量")
    last_message_at = Column(DateTime, nullable=False, default=datetime(2000, 1, 1), comment="最后消息时间")

    __table_args__ = (
        Index("idx_conversation_created_at", "created_at"),
        Index("idx_conversation_last_message_at", "last_message_at"),
        Index("idx_conversation_is_deleted", "is_deleted"),
    )


class Message(BaseModel):
    __tablename__ = "message"

    conversation_id = Column(BigInteger, nullable=False, comment="会话 ID")
    role = Column(String(32), nullable=False, comment="角色 (user/assistant/system/tool)")
    content = Column(Text, nullable=False, comment="消息内容")
    tool_calls = Column(JSON, nullable=False, default=list, comment="工具调用信息")
    tool_call_id = Column(String(128), nullable=False, default="", comment="工具调用响应 ID")
    token_count = Column(Integer, nullable=False, default=0, comment="Token 消耗量")

    __table_args__ = (
        Index("idx_message_conversation_created", "conversation_id", "created_at"),
        Index("idx_message_role", "role"),
    )
