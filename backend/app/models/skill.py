"""技能模型"""
from datetime import datetime

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, Index
from app.models.base import BaseModel


class Skill(BaseModel):
    __tablename__ = "skill"

    name = Column(String(128), nullable=False, unique=True, comment="技能名称")
    display_name = Column(String(256), default="", comment="显示名称")
    description = Column(String(1024), default="", comment="技能描述")
    version = Column(String(32), default="1.0.0", comment="版本号")
    source = Column(String(256), default="", comment="来源")
    trigger_words = Column(JSON, default=list, comment="触发词列表")
    dependencies = Column(JSON, default=list, comment="依赖技能列表")
    is_enabled = Column(Integer, nullable=False, default=1, comment="是否启用: 1=是 0=否")
    config = Column(JSON, nullable=False, default=dict, comment="技能配置")

    __table_args__ = (
        Index("idx_skill_is_deleted_enabled", "is_deleted", "is_enabled"),
    )


class SkillStats(BaseModel):
    __tablename__ = "skill_stat"

    skill_id = Column(BigInteger, nullable=False, comment="技能 ID")
    call_count = Column(Integer, nullable=False, default=0, comment="调用次数")
    success_count = Column(Integer, nullable=False, default=0, comment="成功次数")
    fail_count = Column(Integer, nullable=False, default=0, comment="失败次数")
    avg_duration_ms = Column(Integer, nullable=False, default=0, comment="平均耗时")
    last_called_at = Column(DateTime, nullable=False, default=datetime(2000, 1, 1), server_default='2000-01-01 00:00:00', comment="最后调用时间")

    __table_args__ = (
        Index("idx_skill_stat_skill_id", "skill_id"),
        Index("idx_skill_stat_call_count", "call_count"),
    )
