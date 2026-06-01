"""剪贴板 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


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


class ClipboardItemOut(BaseModel):
    """剪贴板输出"""
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: int
    content: str
    content_type: int
    is_pinned: int
    source_app: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
