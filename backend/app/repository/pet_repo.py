"""宠物属性 Repository"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import PetAttribute, PetInteraction


class PetRepository:
    def __init__(self):
        self.mapper = MySQLMapper(PetAttribute)
        self.interaction_mapper = MySQLMapper(PetInteraction)

    async def get_singleton(self, db: AsyncSession) -> Optional[PetAttribute]:
        """获取宠物属性（单例，ID=1）"""
        return await self.mapper.find_by_id(db, 1)

    async def create_singleton(self, db: AsyncSession) -> PetAttribute:
        """初始化宠物属性（仅首次）"""
        return await self.mapper.create(db, {"id": 1})

    async def update(self, db: AsyncSession, data: dict) -> Optional[PetAttribute]:
        """更新宠物属性"""
        pet = await self.get_singleton(db)
        if not pet:
            pet = await self.create_singleton(db)
        return await self.mapper.update(db, pet.id, data)

    async def create_interaction(self, db: AsyncSession, data: dict) -> PetInteraction:
        """记录互动"""
        return await self.interaction_mapper.create(db, data)

    async def get_interactions(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
    ) -> List[PetInteraction]:
        """查询互动记录"""
        return await self.interaction_mapper.find_all(
            db, offset=offset, limit=limit, order_by=PetInteraction.created_at.desc()
        )
