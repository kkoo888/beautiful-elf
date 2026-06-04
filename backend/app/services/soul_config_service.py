"""人格配置 Service"""
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.soul_config_repo import SoulConfigRepository
from app.schemas.soul_config import SoulConfigCreate, SoulConfigUpdate, SoulConfigOut
from app.core.exceptions import RecordNotFoundError


class SoulConfigService:
    def __init__(self):
        self.repo = SoulConfigRepository()

    async def create(self, db: AsyncSession, data: SoulConfigCreate) -> dict:
        config = await self.repo.create(db, data.model_dump())
        return self._to_dict(config)

    async def get_by_id(self, db: AsyncSession, config_id: int) -> dict:
        config = await self.repo.find_by_id(db, config_id)
        if not config:
            raise RecordNotFoundError("人格配置不存在")
        return self._to_dict(config)

    async def list(self, db: AsyncSession, page: int = 1, page_size: int = 20) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size)
        total = await self.repo.count(db)
        return [self._to_dict(c) for c in items], total

    async def update(self, db: AsyncSession, config_id: int, data: SoulConfigUpdate) -> dict:
        existing = await self.repo.find_by_id(db, config_id)
        if not existing:
            raise RecordNotFoundError("人格配置不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_dict(existing)
        config = await self.repo.update(db, config_id, update_data)
        return self._to_dict(config)

    async def delete(self, db: AsyncSession, config_id: int) -> bool:
        existing = await self.repo.find_by_id(db, config_id)
        if not existing:
            raise RecordNotFoundError("人格配置不存在")
        return await self.repo.soft_delete(db, config_id)

    async def get_active(self, db: AsyncSession) -> dict:
        config = await self.repo.find_active(db)
        if not config:
            return {}
        return self._to_dict(config)

    @staticmethod
    def _to_dict(config) -> dict:
        return SoulConfigOut.model_validate(config).model_dump()
