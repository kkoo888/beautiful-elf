"""提炼记忆关联表 — 借鉴 Hindsight Evidence Grounding

设计动机:
  - 多对多关联：一条 observation 关联多条源 daily log
  - evidence_quote 记录从源日志中提取的关键引用（精确溯源）
  - proof_count 通过 COUNT 查询实时计算，不冗余存储
"""
from sqlalchemy import Column, BigInteger, String, ForeignKey, Index
from app.models.base import BaseModel


class MemoryObservationSource(BaseModel):
    __tablename__ = "memory_observation_source"

    observation_id = Column(BigInteger, nullable=False, comment="→ memory_observation.id")
    source_memory_id = Column(BigInteger, nullable=False, comment="→ markdown_memory.id（daily log）")
    evidence_quote = Column(String(500), nullable=False, default="",
                            comment="从源日志中提取的关键引用")

    __table_args__ = (
        Index("idx_obs_src_obs", "observation_id"),
        Index("idx_obs_src_memory", "source_memory_id"),
        Index("idx_obs_src_is_deleted", "is_deleted"),
    )
