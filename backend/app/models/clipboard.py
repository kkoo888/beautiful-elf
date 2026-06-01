"""剪贴板模型"""
from sqlalchemy import Column, Integer, String, Text, Index
from app.models.base import BaseModel


class ClipboardItem(BaseModel):
    __tablename__ = "clipboard_item"

    content = Column(Text, nullable=False, comment="剪贴板内容")
    content_type = Column(Integer, nullable=False, default=0, comment="内容类型")
    is_pinned = Column(Integer, nullable=False, default=0, comment="是否固定")
    source_app = Column(String(256), default="", comment="来源应用")

    __table_args__ = (
        Index("idx_clipboard_item_is_pinned", "is_pinned"),
        Index("idx_clipboard_item_content_type", "content_type"),
        Index("idx_clipboard_item_created_at", "created_at"),
    )
