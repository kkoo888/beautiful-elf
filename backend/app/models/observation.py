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
    # Phase 2: 时间感知
    valid_from = Column(String(32), nullable=False, default="",
                        comment="生效时间 ISO（从源日志最早时间）")
    valid_until = Column(String(32), nullable=False, default="",
                         comment="失效时间 ISO（被新 observation 替代时设置）")
    superseded_by = Column(BigInteger, nullable=False, default=0,
                           comment="被哪条 observation 替代（0=当前有效）")
    # Phase 1: 实体关联
    entities = Column(String(500), nullable=False, default="",
                      comment="关联实体 ID 列表，逗号分隔")

    __table_args__ = (
        Index("idx_obs_user", "user_id"),
        Index("idx_obs_category", "user_id", "category"),
        Index("idx_obs_freshness", "user_id", "freshness"),
        Index("idx_obs_is_deleted", "is_deleted"),
    )
