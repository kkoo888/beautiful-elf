"""意图模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Numeric, JSON, Index
from app.models.base import BaseModel


class Intent(BaseModel):
    __tablename__ = "intents"

    name = Column(String(128), nullable=False, comment="意图名称")
    description = Column(String(512), default="", comment="意图描述")
    trigger_texts = Column(JSON, nullable=False, comment="触发词列表")
    target_module = Column(String(128), nullable=False, comment="目标模块")
    metadata_ = Column("metadata", JSON, default=None, comment="扩展元数据")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")
    qdrant_point_id = Column(String(128), default=None, comment="Qdrant 向量 ID")

    __table_args__ = (
        Index("idx_intents_enabled", "deleted", "enabled"),
        Index("idx_intents_module", "target_module"),
    )


class IntentUsage(BaseModel):
    __tablename__ = "intent_usage"

    intent_id = Column(BigInteger, nullable=False, comment="意图 ID")
    hit_count = Column(Integer, nullable=False, default=0, comment="命中次数")
    avg_confidence = Column(Numeric(5, 4), nullable=False, default=0.0, comment="平均置信度")
    last_hit_at = Column(DateTime, default=None, comment="最后命中时间")

    __table_args__ = (
        Index("idx_usage_intent", "intent_id"),
        Index("idx_usage_hit_count", "hit_count"),
    )
