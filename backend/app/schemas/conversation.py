"""会话管理 Schema — camelCase 请求/响应"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ConversationCreate(BaseModel):
    """创建会话"""
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(default="", max_length=256, description="会话标题", alias="title")
    model_name: str = Field(default="", max_length=128, description="对话模型", alias="modelName")


class ConversationUpdate(BaseModel):
    """更新会话"""
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = Field(default=None, max_length=256, description="会话标题", alias="title")
    model_name: Optional[str] = Field(default=None, max_length=128, description="对话模型", alias="modelName")


class ConversationOut(BaseModel):
    """会话输出"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    title: str
    model_name: str = Field(alias="modelName")
    message_count: int = Field(alias="messageCount")
    last_message_at: Optional[datetime] = Field(default=None, alias="lastMessageAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
