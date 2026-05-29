"""宠物模型"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, func, Index
from app.models.base import BaseModel


class PetAttribute(BaseModel):
    __tablename__ = "pet_attributes"

    hunger = Column(Integer, nullable=False, default=100, comment="饥饿值 (0-100)")
    clean = Column(Integer, nullable=False, default=100, comment="清洁值 (0-100)")
    mood = Column(Integer, nullable=False, default=100, comment="心情值 (0-100)")
    health = Column(Integer, nullable=False, default=100, comment="健康值 (0-100)")
    intimacy = Column(Integer, nullable=False, default=0, comment="亲密度")
    level = Column(Integer, nullable=False, default=1, comment="等级")
    exp = Column(Integer, nullable=False, default=0, comment="经验值")
    last_active_at = Column(DateTime, nullable=False, server_default=func.now(), comment="最后活跃时间")


class PetInteraction(BaseModel):
    __tablename__ = "pet_interactions"

    pet_attribute_id = Column(BigInteger, nullable=False, comment="宠物属性 ID")
    interaction_type = Column(Integer, nullable=False, comment="互动类型")
    effect_json = Column(JSON, default=None, comment="属性变化效果")

    __table_args__ = (
        Index("idx_pet_interactions_type", "interaction_type"),
        Index("idx_pet_interactions_created", "created_at"),
    )
