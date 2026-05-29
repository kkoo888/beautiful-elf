"""日程管理 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    """创建日程"""
    title: str
    description: str = ""
    start_time: datetime
    end_time: Optional[datetime] = None
    all_day: int = 0
    reminder_minutes: int = 0
    repeat_type: int = 0
    color: str = ""


class ScheduleUpdate(BaseModel):
    """更新日程"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[int] = None
    reminder_minutes: Optional[int] = None
    repeat_type: Optional[int] = None
    color: Optional[str] = None


class ScheduleOut(BaseModel):
    """日程输出"""
    id: int
    title: str
    description: str
    start_time: datetime
    end_time: Optional[datetime]
    all_day: int
    reminder_minutes: int
    reminded: int
    repeat_type: int
    color: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
