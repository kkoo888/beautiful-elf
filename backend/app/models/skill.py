"""技能模型"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, Index
from app.models.base import BaseModel


class Skill(BaseModel):
    __tablename__ = "skills"

    name = Column(String(128), nullable=False, unique=True, comment="技能名称")
    display_name = Column(String(256), default="", comment="显示名称")
    description = Column(String(1024), default="", comment="技能描述")
    version = Column(String(32), default="1.0.0", comment="版本号")
    source = Column(String(256), default="", comment="来源")
    trigger_words = Column(JSON, default=None, comment="触发词列表")
    dependencies = Column(JSON, default=None, comment="依赖技能列表")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")
    config = Column(JSON, default=None, comment="技能配置")

    __table_args__ = (
        Index("idx_skills_enabled", "deleted", "enabled"),
    )


class SkillStats(BaseModel):
    __tablename__ = "skill_stats"

    skill_id = Column(BigInteger, nullable=False, comment="技能 ID")
    call_count = Column(Integer, nullable=False, default=0, comment="调用次数")
    success_count = Column(Integer, nullable=False, default=0, comment="成功次数")
    fail_count = Column(Integer, nullable=False, default=0, comment="失败次数")
    avg_duration_ms = Column(Integer, nullable=False, default=0, comment="平均耗时")
    last_called_at = Column(DateTime, default=None, comment="最后调用时间")

    __table_args__ = (
        Index("idx_skill_stats_skill", "skill_id"),
        Index("idx_skill_stats_calls", "call_count"),
    )
