"""提炼记忆 Repository — CRUD + 关联查询"""
from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.observation import MemoryObservation
from app.models.observation_source import MemoryObservationSource


class ObservationRepository:
    """提炼记忆 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(MemoryObservation)

    # ── CRUD ────────────────────────────────────────────

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[MemoryObservation]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, user_id: int = 0,
        category: Optional[str] = None,
        offset: int = 0, limit: int = 50,
    ) -> List[MemoryObservation]:
        """获取提炼记忆列表"""
        filters = {"user_id": user_id}
        if category and category != "all":
            filters["category"] = category
        return await self.mapper.find_all(
            db, filters=filters, offset=offset, limit=limit,
            order_by=MemoryObservation.created_at.desc(),
        )

    async def count(
        self, db: AsyncSession, user_id: int = 0,
        category: Optional[str] = None,
    ) -> int:
        filters = {"user_id": user_id}
        if category and category != "all":
            filters["category"] = category
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> MemoryObservation:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[MemoryObservation]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    # ── 关联查询 ────────────────────────────────────────

    async def get_proof_count(self, db: AsyncSession, observation_id: int) -> int:
        """获取 observation 的证据条数"""
        stmt = (
            select(func.count())
            .select_from(MemoryObservationSource)
            .where(
                MemoryObservationSource.observation_id == observation_id,
                MemoryObservationSource.is_deleted == 0,
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def get_sources(self, db: AsyncSession, observation_id: int) -> List[MemoryObservationSource]:
        """获取 observation 的所有关联源"""
        stmt = (
            select(MemoryObservationSource)
            .where(
                MemoryObservationSource.observation_id == observation_id,
                MemoryObservationSource.is_deleted == 0,
            )
            .order_by(MemoryObservationSource.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_source_with_daily_log(self, db: AsyncSession, observation_id: int) -> List[dict]:
        """获取关联源 + 对应 daily log 标题（联查）"""
        from app.models.markdown_memory import MarkdownMemory
        stmt = (
            select(
                MemoryObservationSource.id.label("source_id"),
                MemoryObservationSource.evidence_quote,
                MarkdownMemory.title.label("log_title"),
                MarkdownMemory.id.label("log_id"),
            )
            .join(MarkdownMemory, MemoryObservationSource.source_memory_id == MarkdownMemory.id)
            .where(
                MemoryObservationSource.observation_id == observation_id,
                MemoryObservationSource.is_deleted == 0,
                MarkdownMemory.is_deleted == 0,
            )
            .order_by(MarkdownMemory.title.desc())
        )
        result = await db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def create_source(self, db: AsyncSession, data: dict) -> MemoryObservationSource:
        """创建关联记录"""
        mapper = MySQLMapper(MemoryObservationSource)
        return await mapper.create(db, data)

    async def create_sources_batch(self, db: AsyncSession, items: List[dict]) -> int:
        """批量创建关联记录"""
        for item in items:
            await self.create_source(db, item)
        return len(items)

    async def delete_source(self, db: AsyncSession, source_id: int) -> bool:
        """软删除关联记录"""
        mapper = MySQLMapper(MemoryObservationSource)
        return await mapper.soft_delete(db, source_id)

    async def find_by_content_similarity(
        self, db: AsyncSession, user_id: int, content_prefix: str
    ) -> Optional[MemoryObservation]:
        """按内容前缀查找（简易去重）"""
        stmt = (
            select(MemoryObservation)
            .where(
                MemoryObservation.user_id == user_id,
                MemoryObservation.is_deleted == 0,
                MemoryObservation.content.like(f"{content_prefix[:50]}%"),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def count_by_category(self, db: AsyncSession, user_id: int) -> dict:
        """按分类统计数量"""
        stmt = (
            select(MemoryObservation.category, func.count())
            .where(
                MemoryObservation.user_id == user_id,
                MemoryObservation.is_deleted == 0,
            )
            .group_by(MemoryObservation.category)
        )
        result = await db.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
