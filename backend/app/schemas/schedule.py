"""日程管理 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.base import CamelModel


class ScheduleCreate(BaseModel):
    """创建日程"""
    model_config = ConfigDict(populate_by_name=True)

    title: str
    description: str = ""
    start_time: datetime = Field(..., alias="startTime")
    end_time: Optional[datetime] = Field(None, alias="endTime")
    is_all_day: int = Field(0, alias="isAllDay")
    reminder_minutes: int = Field(0, alias="reminderMinutes")
    repeat_type: int = Field(0, alias="repeatType")
    color: str = ""


class ScheduleUpdate(BaseModel):
    """更新日程"""
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = Field(None, alias="startTime")
    end_time: Optional[datetime] = Field(None, alias="endTime")
    is_all_day: Optional[int] = Field(None, alias="isAllDay")
    reminder_minutes: Optional[int] = Field(None, alias="reminderMinutes")
    repeat_type: Optional[int] = Field(None, alias="repeatType")
    color: Optional[str] = None


class ScheduleOut(CamelModel):
    """日程输出"""
    id: int
    title: str
    description: str
    start_time: datetime
    end_time: Optional[datetime]
    is_all_day: int
    reminder_minutes: int
    is_reminded: int
    repeat_type: int
    color: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
