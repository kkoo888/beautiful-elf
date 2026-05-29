"""消息记录 Schema"""
from typing import Optional, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    conversation_id: int = Field(..., description="会话 ID")
    role: str = Field(..., max_length=32, description="角色 (user/assistant/system/tool)")
    content: str = Field(..., description="消息内容")
    tool_calls: Optional[Any] = Field(default=None, description="工具调用信息")
    tool_call_id: Optional[str] = Field(default=None, max_length=128, description="工具调用响应 ID")
    token_count: int = Field(default=0, ge=0, description="Token 消耗量")


class MessageUpdate(BaseModel):
    content: Optional[str] = Field(default=None, description="消息内容")
    tool_calls: Optional[Any] = Field(default=None, description="工具调用信息")
    token_count: Optional[int] = Field(default=None, ge=0, description="Token 消耗量")


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    tool_calls: Optional[Any]
    tool_call_id: Optional[str]
    token_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
