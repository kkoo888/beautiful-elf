"""会话管理 Schema — 统一 camelCase"""
from typing import Optional
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class ConversationCreate(CamelModel):
    """创建会话"""
    title: str = Field(default="", max_length=256, description="会话标题")
    model_name: str = Field(default="", max_length=128, description="对话模型")


class ConversationUpdate(CamelModel):
    """更新会话"""
    title: Optional[str] = Field(default=None, max_length=256, description="会话标题")
    model_name: Optional[str] = Field(default=None, max_length=128, description="对话模型")


class ConversationOut(CamelModel):
    """会话输出"""
    id: int
    title: str
    model_name: str
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
