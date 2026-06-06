"""通知系统 Repository"""
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import Notification


class NotificationRepository:
    def __init__(self):
        self.mapper = MySQLMapper(Notification)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Notification]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        type_: Optional[str] = None, read: Optional[int] = None,
    ) -> List[Notification]:
        filters = {}
        if type_:
            filters["type"] = type_
        if read is not None:
            filters["read"] = read
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, read: Optional[int] = None) -> int:
        filters = {}
        if read is not None:
            filters["read"] = read
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> Notification:
        return await self.mapper.create(db, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def mark_read(self, db: AsyncSession, id: int) -> bool:
        """标记单条已读"""
        stmt = (
            update(Notification)
            .where(Notification.id == id, Notification.is_deleted == 0, Notification.is_read == 0)
            .values(read=1)
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount > 0

    async def mark_all_read(self, db: AsyncSession) -> int:
        """标记全部已读"""
        stmt = (
            update(Notification)
            .where(Notification.is_deleted == 0, Notification.is_read == 0)
            .values(read=1)
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount
