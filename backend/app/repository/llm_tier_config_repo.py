"""Tier 配置 Repository"""
from typing import Optional, List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.llm_tier_config import LLMTierConfig


class LLMTierConfigRepository:
    """模型路由 tier 配置数据访问层"""

    def __init__(self):
        self.mapper = MySQLMapper(LLMTierConfig)

    async def find_by_id(self, db: AsyncSession, config_id: int) -> Optional[LLMTierConfig]:
        """按 ID 查询"""
        return await self.mapper.find_by_id(db, config_id)

    async def find_by_tier(self, db: AsyncSession, tier: str) -> List[LLMTierConfig]:
        """查询某个 tier 的所有配置"""
        stmt = (
            select(LLMTierConfig)
            .where(LLMTierConfig.tier == tier, LLMTierConfig.is_deleted == 0)
            .order_by(LLMTierConfig.id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_all_enabled(self, db: AsyncSession) -> List[LLMTierConfig]:
        """查询所有启用的 tier 配置"""
        stmt = (
            select(LLMTierConfig)
            .where(LLMTierConfig.is_enabled == 1, LLMTierConfig.is_deleted == 0)
            .order_by(LLMTierConfig.tier, LLMTierConfig.id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_provider(self, db: AsyncSession, provider_id: int) -> List[LLMTierConfig]:
        """查询某个供应商的所有 tier 配置"""
        stmt = (
            select(LLMTierConfig)
            .where(LLMTierConfig.provider_id == provider_id, LLMTierConfig.is_deleted == 0)
            .order_by(LLMTierConfig.tier)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_tier_model_map(self, db: AsyncSession) -> Dict[str, dict]:
        """获取 tier → model 映射（用于 model_selector）

        Returns:
            {"S": {"model_name": "qwen3.5:0.8b", "provider_id": 1, "max_tokens": 1024, ...}, ...}
        """
        configs = await self.find_all_enabled(db)
        tier_map = {}
        for c in configs:
            tier_map[c.tier] = {
                "model_name": c.model_name,
                "provider_id": c.provider_id,
                "temperature": c.temperature,
                "reasoning_enabled": c.reasoning_enabled,
                "fallback_model_name": c.fallback_model_name,
            }
        return tier_map

    async def upsert(self, db: AsyncSession, tier: str, provider_id: int, model_name: str, **kwargs) -> LLMTierConfig:
        """创建或更新 tier 配置（按 tier+model_name 去重）"""
        stmt = select(LLMTierConfig).where(
            LLMTierConfig.tier == tier,
            LLMTierConfig.model_name == model_name,
            LLMTierConfig.is_deleted == 0,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        data = {"tier": tier, "provider_id": provider_id, "model_name": model_name, **kwargs}
        if existing:
            return await self.mapper.update(db, existing.id, data)
        return await self.mapper.create(db, data)

    async def delete_by_tier(self, db: AsyncSession, tier: str) -> int:
        """软删除某个 tier 的所有配置（is_deleted=1）"""
        from sqlalchemy import update
        stmt = (
            update(LLMTierConfig)
            .where(LLMTierConfig.tier == tier, LLMTierConfig.is_deleted == 0)
            .values(is_deleted=1)
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount
