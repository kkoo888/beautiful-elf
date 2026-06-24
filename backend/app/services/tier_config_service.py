"""Tier 配置 Service"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.llm_tier_config_repo import LLMTierConfigRepository
from app.schemas.llm_provider import TierConfigCreate, TierConfigUpdate, TierConfigOut
from app.core.exceptions import RecordNotFoundError


class TierConfigService:
    def __init__(self):
        self.repo = LLMTierConfigRepository()

    async def list_all(self, db: AsyncSession) -> List[TierConfigOut]:
        """查询所有启用的 tier 配置"""
        items = await self.repo.find_all_enabled(db)
        return [self._to_out(i) for i in items]

    async def list_by_provider(self, db: AsyncSession, provider_id: int) -> List[TierConfigOut]:
        """查询某个供应商的所有 tier 配置"""
        items = await self.repo.find_by_provider(db, provider_id)
        return [self._to_out(i) for i in items]

    async def get_by_id(self, db: AsyncSession, config_id: int) -> TierConfigOut:
        """按 ID 查询"""
        item = await self.repo.find_by_id(db, config_id)
        if not item:
            raise RecordNotFoundError("Tier 配置不存在")
        return self._to_out(item)

    async def upsert(self, db: AsyncSession, data: TierConfigCreate) -> TierConfigOut:
        """创建或更新 tier 配置"""
        item = await self.repo.upsert(
            db, tier=data.tier, provider_id=data.provider_id,
            model_name=data.model_name,
            fallback_model_name=data.fallback_model_name,
            max_tokens=data.max_tokens,
            temperature=data.temperature,
            reasoning_enabled=data.reasoning_enabled,
            is_enabled=data.is_enabled,
        )
        return self._to_out(item)

    async def update(self, db: AsyncSession, config_id: int, data: TierConfigUpdate) -> TierConfigOut:
        """更新 tier 配置"""
        item = await self.repo.find_by_id(db, config_id)
        if not item:
            raise RecordNotFoundError("Tier 配置不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_out(item)
        updated = await self.repo.mapper.update(db, config_id, update_data)
        return self._to_out(updated)

    async def delete_by_tier(self, db: AsyncSession, tier: str) -> int:
        """删除某个 tier 的所有配置"""
        return await self.repo.delete_by_tier(db, tier)

    async def get_tier_model_map(self, db: AsyncSession) -> dict:
        """获取 tier → model 映射（供 model_selector 使用）"""
        return await self.repo.get_tier_model_map(db)

    @staticmethod
    def _to_out(item) -> TierConfigOut:
        return TierConfigOut.model_validate(item)
