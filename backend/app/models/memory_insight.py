"""洞察模型 — 借鉴 Hindsight Reflect / CARA 信念网络

设计动机:
  - 从记忆中自动提取的模式、趋势、风险
  - 洞察有类型（pattern/trend/risk/insight）
  - 洞察有置信度（随证据强化/弱化）
  - 洞察关联到源 observations
"""
from sqlalchemy import Column, BigInteger, String, Integer, Text, Index
from app.models.base import BaseModel


class MemoryInsight(BaseModel):
    __tablename__ = "memory_insight"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    content = Column(Text, nullable=False, comment="洞察内容")
    insight_type = Column(String(32), nullable=False, default="insight",
                          comment="类型: pattern/trend/risk/insight")
    confidence = Column(Integer, nullable=False, default=50,
                        comment="置信度 0-100（随证据强化/弱化）")
    evidence_count = Column(Integer, nullable=False, default=1, comment="支持证据数")
    source_period = Column(String(64), nullable=False, default="",
                           comment="来源时间范围（如 2026-06-01~2026-06-15）")
    status = Column(String(16), nullable=False, default="active",
                    comment="状态: active/superseded/dismissed")

    __table_args__ = (
        Index("idx_insight_user", "user_id"),
        Index("idx_insight_type", "user_id", "insight_type"),
        Index("idx_insight_status", "user_id", "status"),
        Index("idx_insight_is_deleted", "is_deleted"),
    )
