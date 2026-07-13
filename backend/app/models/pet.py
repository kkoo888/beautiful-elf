"""宠物模型"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, JSON, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class InteractionType(enum.IntEnum):
    """互动类型枚举"""
    FEED = 0
    CLEAN = 1
    CHAT = 2
    PLAY = 3


# 互动类型 → 名称映射
INTERACTION_TYPE_NAMES: dict[int, str] = {
    InteractionType.FEED: "feed",
    InteractionType.CLEAN: "clean",
    InteractionType.CHAT: "chat",
    InteractionType.PLAY: "play",
}

# 互动类型 → 效果描述
INTERACTION_EFFECT_DESC: dict[int, str] = {
    InteractionType.FEED: "饥饿度 +20",
    InteractionType.CLEAN: "清洁度 +20",
    InteractionType.CHAT: "心情 +15, 亲密 +5, 健康 +5（饥饿>30且清洁>40时）",
    InteractionType.PLAY: "心情 +25, 经验 +10（可触发升级，等级*100 为升级阈值）",
}


class PetAttribute(BaseModel):
    __tablename__ = "pet_attribute"

    hunger: Mapped[int] = mapped_column(Integer, nullable=False, default=100, comment="饥饿值 (0-100)")
    clean: Mapped[int] = mapped_column(Integer, nullable=False, default=100, comment="清洁值 (0-100)")
    mood: Mapped[int] = mapped_column(Integer, nullable=False, default=100, comment="心情值 (0-100)")
    health: Mapped[int] = mapped_column(Integer, nullable=False, default=100, comment="健康值 (0-100)")
    intimacy: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="亲密度")
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="等级")
    exp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="经验值")
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="最后活跃时间"
    )


class PetInteraction(BaseModel):
    __tablename__ = "pet_interaction"

    pet_attribute_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="宠物属性 ID")
    interaction_type: Mapped[int] = mapped_column(Integer, nullable=False, comment="互动类型")
    effect_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=False, default=dict, comment="属性变化效果")

    __table_args__ = (
        Index("idx_pet_interaction_type", "interaction_type"),
        Index("idx_pet_interaction_created_at", "created_at"),
    )
