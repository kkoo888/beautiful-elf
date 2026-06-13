"""日程模型"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Index
from app.models.base import BaseModel


class Schedule(BaseModel):
    __tablename__ = "schedule"

    title = Column(String(256), nullable=False, comment="日程标题")
    description = Column(String(2048), default="", comment="日程描述")
    start_time = Column(DateTime, nullable=False, comment="开始时间")
    end_time = Column(DateTime, nullable=False, default=datetime(2000, 1, 1), comment="结束时间 (全天事件用 start_time)")
    is_all_day = Column(Integer, nullable=False, default=0, comment="是否全天事件: 1=是 0=否")
    reminder_minutes = Column(Integer, nullable=False, default=0, comment="提前提醒时间 (分钟)")
    is_reminded = Column(Integer, nullable=False, default=0, comment="是否已提醒: 1=是 0=否")
    repeat_type = Column(Integer, nullable=False, default=0, comment="重复类型")
    color = Column(String(16), nullable=False, default="", comment="颜色标记")

    __table_args__ = (
        Index("idx_schedule_start_time", "start_time"),
        Index("idx_schedule_reminder", "is_reminded", "reminder_minutes", "start_time"),
        Index("idx_schedule_is_deleted", "is_deleted"),
    )
