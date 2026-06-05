"""长期记忆 Repository — 封装 MemoryEntry CRUD"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.memory import MemoryEntry


class MemoryRepository:
    """长期记忆 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(MemoryEntry)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[MemoryEntry]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        conversation_id: Optional[int] = None,
    ) -> List[MemoryEntry]:
        filters = {}
        if conversation_id is not None:
            filters["conversation_id"] = conversation_id
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, conversation_id: Optional[int] = None) -> int:
        filters = {}
        if conversation_id is not None:
            filters["conversation_id"] = conversation_id
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> MemoryEntry:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[MemoryEntry]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)
