"""会话管理 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="", max_length=256, description="会话标题")
    model_name: str = Field(default="", max_length=128, description="对话模型")


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=256, description="会话标题")
    model_name: Optional[str] = Field(default=None, max_length=128, description="对话模型")


class ConversationOut(BaseModel):
    id: int
    title: str
    model_name: str
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
