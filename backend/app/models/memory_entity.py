"""实体记忆模型 — 借鉴 Hindsight TEMPR 实体抽取

设计动机:
  - 从 observations 中自动抽取实体（人/技术/项目/工具/概念）
  - 每个实体有类型、属性、描述
  - 实体是关系图谱的节点
"""
from sqlalchemy import Column, BigInteger, String, Text, Index
from app.models.base import BaseModel


class MemoryEntity(BaseModel):
    __tablename__ = "memory_entity"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    name = Column(String(128), nullable=False, comment="实体名称")
    entity_type = Column(String(32), nullable=False, default="concept",
                         comment="实体类型: person/tech/project/tool/concept/org")
    description = Column(Text, nullable=False, default="", comment="实体描述（自动/手动）")
    aliases = Column(String(500), nullable=False, default="",
                     comment="别名，逗号分隔（如 React,react.js）")
    mention_count = Column(BigInteger, nullable=False, default=1, comment="被提及次数")
    last_mentioned_at = Column(String(32), nullable=False, default="",
                               comment="最后提及时间 ISO")

    __table_args__ = (
        Index("idx_entity_user", "user_id"),
        Index("idx_entity_type", "user_id", "entity_type"),
        Index("idx_entity_name", "user_id", "name", unique=True),
        Index("idx_entity_is_deleted", "is_deleted"),
    )
