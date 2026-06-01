"""剪贴板 Repository"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import ClipboardItem


class ClipboardRepository:
    def __init__(self):
        self.mapper = MySQLMapper(ClipboardItem)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[ClipboardItem]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        content_type: Optional[int] = None, pinned: Optional[int] = None,
    ) -> List[ClipboardItem]:
        filters = {}
        if content_type is not None:
            filters["content_type"] = content_type
        if pinned is not None:
            filters["pinned"] = pinned
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, content_type: Optional[int] = None) -> int:
        filters = {}
        if content_type is not None:
            filters["content_type"] = content_type
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> ClipboardItem:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[ClipboardItem]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def toggle_pin(self, db: AsyncSession, id: int) -> Optional[ClipboardItem]:
        item = await self.find_by_id(db, id)
        if not item:
            return None
        return await self.mapper.update(db, id, {"is_pinned": 0 if item.is_pinned else 1})
