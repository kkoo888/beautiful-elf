"""通知系统 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.base import CamelModel


class NotificationCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(default="", max_length=128, description="事件去重 ID", alias="eventId")
    type: str = Field(..., max_length=32, description="通知类型")
    title: str = Field(..., max_length=256, description="通知标题")
    message: str = Field(..., description="通知内容")
    action_url: str = Field(default="", max_length=512, description="跳转地址", alias="actionUrl")


class NotificationUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(default=None, max_length=32, description="通知类型")
    title: Optional[str] = Field(default=None, max_length=256, description="通知标题")
    message: Optional[str] = Field(default=None, description="通知内容")
    action_url: Optional[str] = Field(default=None, max_length=512, description="跳转地址", alias="actionUrl")


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
