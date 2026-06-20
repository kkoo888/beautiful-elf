"""实体关系模型 — 借鉴 Hindsight TEMPR 关系图谱 + Zep Graphiti Bi-Temporal

设计动机:
  - 实体间的关系（使用/依赖/属于/创建/就职于）
  - 关系有类型、权重（被验证次数）、来源
  - 支持图谱遍历查询
  - v5.1: Bi-Temporal Edge (valid_at/invalid_at) 支持时间推理
"""
from sqlalchemy import Column, BigInteger, String, Integer, Text, DateTime, Index
from app.models.base import BaseModel


class MemoryEntityRelation(BaseModel):
    __tablename__ = "memory_entity_relation"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    source_entity_id = Column(BigInteger, nullable=False, comment="源实体 ID")
    target_entity_id = Column(BigInteger, nullable=False, comment="目标实体 ID")
    relation_type = Column(String(32), nullable=False, default="related",
                           comment="关系类型: uses/depends/belongs/creates/works_at/related/causes/enables/prevents")
    weight = Column(Integer, nullable=False, default=1, comment="权重（被验证次数）")
    evidence = Column(Text, nullable=False, default="", comment="关系证据（来源内容摘要）")
    source_obs_id = Column(BigInteger, nullable=False, default=0,
                           comment="来源 observation ID（0=手动创建）")

    # v5.1: Bi-Temporal Edge（借鉴 Zep Graphiti）
    valid_at = Column(DateTime, nullable=True, comment="关系生效时间（NULL=未知）")
    invalid_at = Column(DateTime, nullable=True, comment="关系失效时间（NULL=仍有效）")

    __table_args__ = (
        Index("idx_rel_user", "user_id"),
        Index("idx_rel_source", "source_entity_id"),
        Index("idx_rel_target", "target_entity_id"),
        Index("idx_rel_pair", "source_entity_id", "target_entity_id", "relation_type"),
        Index("idx_rel_is_deleted", "is_deleted"),
        Index("idx_rel_valid_at", "valid_at"),
        Index("idx_rel_invalid_at", "invalid_at"),
    )
