"""日程模型"""
from sqlalchemy import Column, Integer, String, DateTime, Index
from app.models.base import BaseModel


class Schedule(BaseModel):
    __tablename__ = "schedules"

    title = Column(String(256), nullable=False, comment="日程标题")
    description = Column(String(2048), default="", comment="日程描述")
    start_time = Column(DateTime, nullable=False, comment="开始时间")
    end_time = Column(DateTime, default=None, comment="结束时间")
    all_day = Column(Integer, nullable=False, default=0, comment="是否全天事件")
    reminder_minutes = Column(Integer, default=0, comment="提前提醒时间 (分钟)")
    reminded = Column(Integer, nullable=False, default=0, comment="是否已提醒")
    repeat_type = Column(Integer, nullable=False, default=0, comment="重复类型")
    color = Column(String(16), default="", comment="颜色标记")

    __table_args__ = (
        Index("idx_schedules_start", "start_time"),
        Index("idx_schedules_reminder", "reminded", "reminder_minutes", "start_time"),
        Index("idx_schedules_deleted", "deleted"),
    )
