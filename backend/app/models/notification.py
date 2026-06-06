"""通知模型"""
from sqlalchemy import Column, Integer, String, Text, Index
from app.models.base import BaseModel


class Notification(BaseModel):
    __tablename__ = "notification"

    event_id = Column(String(128), default="", comment="事件去重 ID")
    type = Column(String(32), nullable=False, comment="通知类型")
    title = Column(String(256), nullable=False, comment="通知标题")
    message = Column(Text, nullable=False, comment="通知内容")
    is_read = Column(Integer, nullable=False, default=0, comment="是否已读: 1=是 0=否")
    action_url = Column(String(512), default="", comment="跳转地址")

    __table_args__ = (
        Index("idx_notification_type_is_read", "type", "is_read"),
        Index("idx_notification_created_at", "created_at"),
    )
