"""操作日志模型"""
from sqlalchemy import Column, String, Index
from app.models.base import BaseModel


class ActionLog(BaseModel):
    __tablename__ = "action_logs"

    module = Column(String(64), nullable=False, comment="模块名")
    action = Column(String(128), nullable=False, comment="行为动作")
    params_summary = Column(String(512), default="", comment="参数摘要 (已脱敏)")
    session_id = Column(String(128), default="", comment="会话 ID")

    __table_args__ = (
        Index("idx_action_logs_module", "module"),
        Index("idx_action_logs_created", "created_at"),
        Index("idx_action_logs_action", "action"),
    )
