"""意图学习模型 — 纠正历史 / 行为模式 / 技能建议

ProactiveAgent 借鉴：
  - skill_suggestion: ignore_count + last_feedback（用户反馈循环）
  - behavior_pattern: is_solved（模式已被技能覆盖标记）
"""
from sqlalchemy import Column, BigInteger, Integer, String, JSON, Index
from app.models.base import BaseModel


class IntentCorrection(BaseModel):
    """意图纠正记录"""
    __tablename__ = "intent_correction"

    original_intent = Column(String(512), nullable=False, default="", comment="原始意图文本")
    correct_module = Column(String(128), nullable=False, default="", comment="纠正后的目标模块")
    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")

    __table_args__ = (
        Index("idx_intent_correction_user_id", "user_id"),
        Index("idx_intent_correction_is_deleted", "is_deleted"),
    )


class BehaviorPattern(BaseModel):
    """行为模式"""
    __tablename__ = "behavior_pattern"

    description = Column(String(512), nullable=False, default="", comment="模式描述")
    frequency = Column(Integer, nullable=False, default=0, comment="触发频率")
    actions = Column(JSON, nullable=False, default=list, comment="动作序列")
    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    is_solved = Column(Integer, nullable=False, default=0, comment="是否已被技能覆盖: 1=是 0=否")

    __table_args__ = (
        Index("idx_behavior_pattern_user_id", "user_id"),
        Index("idx_behavior_pattern_frequency", "frequency"),
    )


class SkillSuggestion(BaseModel):
    """技能建议"""
    __tablename__ = "skill_suggestion"

    pattern_id = Column(BigInteger, nullable=False, default=0, comment="关联的行为模式 ID")
    name = Column(String(128), nullable=False, default="", comment="建议技能名称")
    description = Column(String(512), nullable=False, default="", comment="建议描述")
    status = Column(Integer, nullable=False, default=0, comment="状态: 0=待处理 1=已接受 2=已忽略")
    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    ignore_count = Column(Integer, nullable=False, default=0, comment="连续忽略次数")
    last_feedback = Column(String(32), nullable=False, default="", comment="最近反馈: accepted/ignored")

    __table_args__ = (
        Index("idx_skill_suggestion_user_id", "user_id"),
        Index("idx_skill_suggestion_status", "status"),
        Index("idx_skill_suggestion_pattern_id", "pattern_id"),
    )
