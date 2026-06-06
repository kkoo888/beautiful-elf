"""人格配置 Repository"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import SoulConfig


class SoulConfigRepository:
    def __init__(self):
        self.mapper = MySQLMapper(SoulConfig)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[SoulConfig]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(self, db: AsyncSession, offset: int = 0, limit: int = 20) -> List[SoulConfig]:
        return await self.mapper.find_all(db, offset=offset, limit=limit)

    async def count(self, db: AsyncSession) -> int:
        return await self.mapper.count(db)

    async def create(self, db: AsyncSession, data: dict) -> SoulConfig:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[SoulConfig]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def find_active(self, db: AsyncSession) -> Optional[SoulConfig]:
        """获取当前激活的人格配置"""
        from sqlalchemy import select
        stmt = select(SoulConfig).where(
            SoulConfig.is_active == 1, SoulConfig.is_deleted == 0
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
