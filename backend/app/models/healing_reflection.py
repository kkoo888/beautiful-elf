"""自愈反思记忆模型 — Reflexion 模式

设计依据:
  - Reflexion 论文: Language Agents with Verbal Reinforcement Learning
  - CrewAI Guardrail 模式
  - 2026 行业最佳实践

存储策略:
  - 短期反思: Redis (TTL 30min, key=healing:goal:{goal_id})
  - 长期反思: MySQL (本表, 持久化 + 结构化查询)
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, JSON, DateTime, Index
from app.models.base import BaseModel


class HealingReflection(BaseModel):
    __tablename__ = "healing_reflection"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    failure_type = Column(String(32), nullable=False, default="",
                          comment="失败类型: tool_error/guardrail_fail/llm_error/timeout/empty_output/incomplete/irrelevant")
    trigger_cond = Column(String(500), nullable=False, default="", comment="触发条件")
    what_not_to_do = Column(String(500), nullable=False, default="", comment="避免的错误")
    suggested_strategy = Column(String(500), nullable=False, default="", comment="建议策略")
    confidence = Column(Integer, nullable=False, default=70, comment="置信度 0-100")
    scope_tags = Column(JSON, nullable=False, default=list, comment='作用域标签 ["guardrail","tool_error"]')
    subtask_id = Column(BigInteger, nullable=False, default=0, comment="关联子任务 ID")
    subtask_title = Column(String(256), nullable=False, default="", comment="子任务标题")
    goal_definition = Column(String(1000), nullable=False, default="", comment="目标描述")
    retry_count = Column(Integer, nullable=False, default=0, comment="已重试次数")
    was_successful = Column(Integer, nullable=False, default=0, comment="后续是否成功: 0=否 1=是")
    ttl_seconds = Column(Integer, nullable=False, default=3600, comment="有效期秒数")
    expired_at = Column(DateTime, nullable=False, default="1970-01-01 00:00:00", comment="过期时间")

    __table_args__ = (
        Index("idx_healing_reflection_user", "user_id"),
        Index("idx_healing_reflection_type", "user_id", "failure_type"),
        Index("idx_healing_reflection_expired", "expired_at"),
        Index("idx_healing_reflection_deleted", "is_deleted"),
    )
