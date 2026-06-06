"""Markdown 记忆文件 Repository"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.mappers.base import MySQLMapper
from app.models.markdown_memory import MarkdownMemory


class MarkdownMemoryRepository:
    """Markdown 记忆文件 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(MarkdownMemory)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[MarkdownMemory]:
        return await self.mapper.find_by_id(db, id)

    async def find_by_title(self, db: AsyncSession, user_id: int, title: str) -> Optional[MarkdownMemory]:
        """按标题查找（如 daily log: 2026-06-06）"""
        filters = {"user_id": user_id, "title": title}
        results = await self.mapper.find_all(db, filters=filters, offset=0, limit=1)
        return results[0] if results else None

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        user_id: Optional[int] = None, memory_type: Optional[str] = None,
    ) -> List[MarkdownMemory]:
        filters = {}
        if user_id is not None:
            filters["user_id"] = user_id
        if memory_type is not None:
            filters["memory_type"] = memory_type
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, user_id: Optional[int] = None, memory_type: Optional[str] = None) -> int:
        filters = {}
        if user_id is not None:
            filters["user_id"] = user_id
        if memory_type is not None:
            filters["memory_type"] = memory_type
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> MarkdownMemory:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[MarkdownMemory]:
        return await self.mapper.update(db, id, data)

    async def upsert(self, db: AsyncSession, user_id: int, title: str, content: str, memory_type: str = "daily") -> MarkdownMemory:
        """按标题 upsert（存在则更新，不存在则创建）"""
        existing = await self.find_by_title(db, user_id, title)
        if existing:
            return await self.mapper.update(db, existing.id, {
                "content": content,
                "word_count": len(content),
                "qdrant_synced": 0,
            })
        return await self.mapper.create(db, {
            "user_id": user_id,
            "title": title,
            "content": content,
            "memory_type": memory_type,
            "word_count": len(content),
        })

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def find_unsynced(self, db: AsyncSession, limit: int = 50) -> List[MarkdownMemory]:
        """查找未同步到 Qdrant 的记录"""
        stmt = (
            select(MarkdownMemory)
            .where(MarkdownMemory.qdrant_synced == 0, MarkdownMemory.is_deleted == 0)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def mark_synced(self, db: AsyncSession, id: int) -> None:
        """标记为已同步"""
        await self.mapper.update(db, id, {"qdrant_synced": 1})
