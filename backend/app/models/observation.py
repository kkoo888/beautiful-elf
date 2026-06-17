"""提炼记忆模型 — 借鉴 Hindsight Observations

设计动机:
  - 每条提炼记忆（observation）对应一条从 daily log 中提炼出的长期知识
  - 通过 memory_observation_source 关联到多条源日志（多对多）
  - freshness 跟踪信念的新鲜度趋势
  - category 分类（decisions/pitfalls/preferences/status）
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Index
from app.models.base import BaseModel


class MemoryObservation(BaseModel):
    __tablename__ = "memory_observation"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    content = Column(Text, nullable=False, comment="提炼内容（Markdown）")
    category = Column(String(32), nullable=False, default="decisions",
                      comment="分类: decisions/pitfalls/preferences/status")
    freshness = Column(String(16), nullable=False, default="new",
                       comment="新鲜度: new/stable/strengthening/weakening/stale")
    source_days = Column(Integer, nullable=False, default=0, comment="来源日志天数")

    __table_args__ = (
        Index("idx_obs_user", "user_id"),
        Index("idx_obs_category", "user_id", "category"),
        Index("idx_obs_freshness", "user_id", "freshness"),
        Index("idx_obs_is_deleted", "is_deleted"),
    )
