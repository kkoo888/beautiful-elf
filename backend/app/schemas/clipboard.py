"""剪贴板 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ClipboardItemCreate(BaseModel):
    """创建剪贴板条目"""
    content: str
    content_type: int = 0
    source_app: str = ""


class ClipboardItemUpdate(BaseModel):
    """更新剪贴板条目"""
    content: Optional[str] = None
    content_type: Optional[int] = None
    source_app: Optional[str] = None


class ClipboardItemPin(BaseModel):
    """固定/取消固定"""
    pinned: int


class ClipboardItemOut(BaseModel):
    """剪贴板输出"""
    id: int
    content: str
    content_type: int
    pinned: int
    source_app: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
