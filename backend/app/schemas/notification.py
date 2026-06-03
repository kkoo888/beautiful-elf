"""通知系统 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class NotificationCreate(CamelModel):
    event_id: str = Field(default="", max_length=128, description="事件去重 ID")
    type: str = Field(..., max_length=32, description="通知类型")
    title: str = Field(..., max_length=256, description="通知标题")
    message: str = Field(..., description="通知内容")
    action_url: str = Field(default="", max_length=512, description="跳转地址")


class NotificationUpdate(CamelModel):
    type: Optional[str] = Field(default=None, max_length=32, description="通知类型")
    title: Optional[str] = Field(default=None, max_length=256, description="通知标题")
    message: Optional[str] = Field(default=None, description="通知内容")
    action_url: Optional[str] = Field(default=None, max_length=512, description="跳转地址")


class NotificationOut(CamelModel):
    id: int
    event_id: str
    type: str
    title: str
    message: str
    is_read: int
    action_url: str
    created_at: datetime
    updated_at: datetime
