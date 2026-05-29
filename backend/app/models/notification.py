"""通知模型"""
from sqlalchemy import Column, Integer, String, Text, Index
from app.models.base import BaseModel


class Notification(BaseModel):
    __tablename__ = "notifications"

    event_id = Column(String(128), default="", comment="事件去重 ID")
    type = Column(String(32), nullable=False, comment="通知类型")
    title = Column(String(256), nullable=False, comment="通知标题")
    message = Column(Text, nullable=False, comment="通知内容")
    read = Column(Integer, nullable=False, default=0, comment="是否已读")
    action_url = Column(String(512), default="", comment="跳转地址")

    __table_args__ = (
        Index("idx_notifications_type", "type"),
        Index("idx_notifications_read", "read"),
        Index("idx_notifications_created", "created_at"),
    )
