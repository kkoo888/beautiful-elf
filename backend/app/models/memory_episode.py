"""Episode 对话分组模型 — 借鉴 Zep Graphiti Episode 节点

设计动机:
  - 对话级记忆聚合（一次对话 → 一个 Episode）
  - bi-temporal 时间模型: started_at = valid_at（对话实际发生时间）
  - 实体关联: entity_ids 存入 Qdrant payload + keyword 索引
  - Observation 关联: distill 产出时自动关联 observation_ids

参考:
  - Zep Graphiti: Episode Node + Entity Edge + Community Detection
  - GraphMem (2026): temporal precedence 自动替代
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, JSON, DateTime, Index
from app.models.base import BaseModel


class MemoryEpisode(BaseModel):
    __tablename__ = "memory_episode"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    conversation_id = Column(BigInteger, nullable=False, comment="来源会话 ID")
    title = Column(String(256), nullable=False, default="", comment="Episode 标题")
    summary = Column(Text, nullable=False, comment="Episode 摘要")
    # bi-temporal: started_at = valid_at（对话实际发生时间）
    started_at = Column(DateTime, nullable=False, comment="对话开始时间 (valid_at)")
    ended_at = Column(DateTime, nullable=False, comment="对话结束时间")
    message_count = Column(Integer, nullable=False, default=0, comment="消息数")
    entity_ids = Column(String(500), nullable=False, default="",
                        comment="关联实体 ID（逗号分隔）")
    observation_ids = Column(String(500), nullable=False, default="",
                             comment="关联 observation ID（逗号分隔）")
    tags = Column(JSON, nullable=False, default=list, comment="话题标签")
    qdrant_point_id = Column(String(128), nullable=False, default="",
                              comment="Qdrant 向量 ID")

    __table_args__ = (
        Index("idx_episode_conv", "conversation_id", unique=True),
        Index("idx_episode_user", "user_id"),
        Index("idx_episode_time", "user_id", "started_at"),
        Index("idx_episode_is_deleted", "is_deleted"),
    )
