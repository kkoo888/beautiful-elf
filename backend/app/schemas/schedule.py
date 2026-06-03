"""日程管理 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class ScheduleCreate(CamelModel):
    """创建日程"""
    title: str
    description: str = ""
    start_time: datetime
    end_time: Optional[datetime] = None
    is_all_day: int = 0
    reminder_minutes: int = 0
    repeat_type: int = 0
    color: str = ""


class ScheduleUpdate(CamelModel):
    """更新日程"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: Optional[int] = None
    reminder_minutes: Optional[int] = None
    repeat_type: Optional[int] = None
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
