"""代码片段 Repository"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import Snippet, SnippetTag


class SnippetRepository:
    def __init__(self):
        self.mapper = MySQLMapper(Snippet)
        self.tag_mapper = MySQLMapper(SnippetTag)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Snippet]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        language: Optional[str] = None, tag: Optional[str] = None,
    ) -> List[Snippet]:
        if tag:
            # 按标签筛选需要 join
            stmt = (
                select(Snippet)
                .join(SnippetTag, SnippetTag.snippet_id == Snippet.id)
                .where(Snippet.deleted == 0, SnippetTag.deleted == 0, SnippetTag.tag == tag)
                .order_by(Snippet.use_count.desc())
                .offset(offset).limit(limit)
            )
            # 需要传入 db 执行
            result = await db.execute(stmt)
            return list(result.scalars().all())
        filters = {}
        if language:
            filters["language"] = language
        return await self.mapper.find_all(
            db, filters=filters, offset=offset, limit=limit, order_by=Snippet.use_count.desc()
        )

    async def count(self, db: AsyncSession) -> int:
        return await self.mapper.count(db)

    async def create(self, db: AsyncSession, data: dict, tags: List[str] = None) -> Snippet:
        snippet = await self.mapper.create(db, data)
        if tags:
            for tag in tags:
                await self.tag_mapper.create(db, {"snippet_id": snippet.id, "tag": tag})
        return snippet

    async def update(self, db: AsyncSession, id: int, data: dict, tags: List[str] = None) -> Optional[Snippet]:
        snippet = await self.mapper.update(db, id, data)
        if tags is not None:
            # 删除旧标签，重新创建
            await self.tag_mapper.soft_delete(db, id)  # 简化处理
            for tag in tags:
                await self.tag_mapper.create(db, {"snippet_id": id, "tag": tag})
        return snippet

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def increment_use_count(self, db: AsyncSession, id: int) -> None:
        snippet = await self.find_by_id(db, id)
        if snippet:
            await self.mapper.update(db, id, {"use_count": snippet.use_count + 1})

    async def get_tags(self, db: AsyncSession, snippet_id: int) -> List[str]:
        """获取片段的所有标签"""
        stmt = select(SnippetTag.tag).where(
            SnippetTag.snippet_id == snippet_id, SnippetTag.deleted == 0
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.all()]
