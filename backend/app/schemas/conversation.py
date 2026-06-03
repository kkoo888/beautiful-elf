"""会话管理 Schema — camelCase 请求/响应"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.base import CamelModel


class ConversationCreate(BaseModel):
    """创建会话"""
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(default="", max_length=256, description="会话标题")
    model_name: str = Field(default="", max_length=128, description="对话模型", alias="modelName")


class ConversationUpdate(BaseModel):
    """更新会话"""
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = Field(default=None, max_length=256, description="会话标题")
    model_name: Optional[str] = Field(default=None, max_length=128, description="对话模型", alias="modelName")


class ConversationOut(CamelModel):
    """会话输出"""
    id: int
    title: str
    model_name: str
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
