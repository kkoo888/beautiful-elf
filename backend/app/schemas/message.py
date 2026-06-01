"""消息记录 Schema — camelCase 请求/响应"""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MessageCreate(BaseModel):
    """创建消息"""
    model_config = ConfigDict(populate_by_name=True)

    conversation_id: Optional[int] = Field(default=None, description="会话 ID（由路径提供，body 中可省略）", alias="conversationId")
    role: str = Field(..., max_length=32, description="角色 (user/assistant/system/tool)")
    content: str = Field(..., description="消息内容")
    tool_calls: Optional[Any] = Field(default=None, description="工具调用信息", alias="toolCalls")
    tool_call_id: Optional[str] = Field(default=None, max_length=128, description="工具调用响应 ID", alias="toolCallId")
    token_count: int = Field(default=0, ge=0, description="Token 消耗量", alias="tokenCount")


class MessageUpdate(BaseModel):
    """更新消息"""
    model_config = ConfigDict(populate_by_name=True)

    content: Optional[str] = Field(default=None, description="消息内容")
    tool_calls: Optional[Any] = Field(default=None, description="工具调用信息", alias="toolCalls")
    token_count: Optional[int] = Field(default=None, description="Token 消耗量", alias="tokenCount")


class MessageOut(BaseModel):
    """消息输出"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    conversation_id: int = Field(alias="conversationId")
    role: str
    content: str
    tool_calls: Optional[Any] = Field(default=None, alias="toolCalls")
    tool_call_id: Optional[str] = Field(default=None, alias="toolCallId")
    token_count: int = Field(alias="tokenCount")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
