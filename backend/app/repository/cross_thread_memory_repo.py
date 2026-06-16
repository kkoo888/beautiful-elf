"""跨线程记忆 Repository — 封装 CrossThreadMemory CRUD"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.cross_thread_memory import CrossThreadMemory


class CrossThreadMemoryRepository:
    """跨线程记忆 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(CrossThreadMemory)

    async def create(self, db: AsyncSession, data: dict) -> CrossThreadMemory:
        return await self.mapper.create(db, data)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[CrossThreadMemory]:
        return await self.mapper.find_by_id(db, id)

    async def find_by_user(
        self, db: AsyncSession, user_id: int, namespace: str = "conversations",
        offset: int = 0, limit: int = 10,
    ) -> List[CrossThreadMemory]:
        return await self.mapper.find_all(
            db,
            filters={"user_id": user_id, "namespace": namespace},
            offset=offset,
            limit=limit,
        )

    async def count_by_user(self, db: AsyncSession, user_id: int, namespace: str = "conversations") -> int:
        return await self.mapper.count(db, filters={"user_id": user_id, "namespace": namespace})

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[CrossThreadMemory]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)
