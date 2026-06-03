"""剪贴板 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class ClipboardItemCreate(CamelModel):
    """创建剪贴板条目"""
    content: str
    content_type: int = Field(0)
    source_app: str = Field("")


class ClipboardItemUpdate(CamelModel):
    """更新剪贴板条目"""
    content: Optional[str] = None
    content_type: Optional[int] = None
    source_app: Optional[str] = None


class ClipboardItemPin(CamelModel):
    """固定/取消固定"""
    is_pinned: int


class ClipboardItemOut(CamelModel):
    """剪贴板输出"""
    id: int
    content: str
    content_type: int
    is_pinned: int
    source_app: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
