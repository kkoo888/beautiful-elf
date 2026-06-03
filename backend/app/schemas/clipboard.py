"""剪贴板 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.base import CamelModel, to_camel


class ClipboardItemCreate(BaseModel):
    """创建剪贴板条目"""
    model_config = ConfigDict(populate_by_name=True)

    content: str
    content_type: int = Field(0, alias="contentType")
    source_app: str = Field("", alias="sourceApp")


class ClipboardItemUpdate(BaseModel):
    """更新剪贴板条目"""
    model_config = ConfigDict(populate_by_name=True)

    content: Optional[str] = None
    content_type: Optional[int] = Field(None, alias="contentType")
    source_app: Optional[str] = Field(None, alias="sourceApp")


class ClipboardItemPin(BaseModel):
    """固定/取消固定"""
    model_config = ConfigDict(populate_by_name=True)

    is_pinned: int = Field(..., alias="isPinned")


class ClipboardItemOut(CamelModel):
    """剪贴板输出"""
    id: int
    content: str
    content_type: int
    is_pinned: int
    source_app: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
