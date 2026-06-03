"""代码片段 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.snippet_repo import SnippetRepository
from app.schemas.snippet import SnippetCreate, SnippetUpdate, SnippetOut
from app.core.exceptions import RecordNotFoundError


class SnippetService:
    def __init__(self):
        self.repo = SnippetRepository()

    @staticmethod
    def _serialize(s, tags: list = None) -> dict:
        d = SnippetOut.model_validate(s).model_dump(by_alias=True)
        if tags is not None:
            d["tags"] = tags
        return d

    async def create(self, db: AsyncSession, data: SnippetCreate) -> dict:
        snippet_data = data.model_dump(exclude={"tags"})
        snippet = await self.repo.create(db, snippet_data, tags=data.tags)
        return self._serialize(snippet, tags=data.tags or [])

    async def get_by_id(self, db: AsyncSession, snippet_id: int) -> dict:
        snippet = await self.repo.find_by_id(db, snippet_id)
        if not snippet:
            raise RecordNotFoundError("代码片段不存在")
        tags = await self.repo.get_tags(db, snippet_id)
        return self._serialize(snippet, tags=tags)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        language: Optional[str] = None, tag: Optional[str] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, language=language, tag=tag)
        total = await self.repo.count(db)
        result = []
        for s in items:
            tags = await self.repo.get_tags(db, s.id)
            result.append(self._serialize(s, tags=tags))
        return result, total

    async def update(self, db: AsyncSession, snippet_id: int, data: SnippetUpdate) -> dict:
        existing = await self.repo.find_by_id(db, snippet_id)
        if not existing:
            raise RecordNotFoundError("代码片段不存在")
        update_data = data.model_dump(exclude_unset=True, exclude={"tags"})
        tags = data.tags if data.tags is not None else None
        snippet = await self.repo.update(db, snippet_id, update_data, tags=tags)
        result_tags = await self.repo.get_tags(db, snippet_id)
        return self._serialize(snippet, tags=result_tags)

    async def delete(self, db: AsyncSession, snippet_id: int) -> bool:
        existing = await self.repo.find_by_id(db, snippet_id)
        if not existing:
            raise RecordNotFoundError("代码片段不存在")
        return await self.repo.soft_delete(db, snippet_id)

    async def increment_use(self, db: AsyncSession, snippet_id: int) -> dict:
        snippet = await self.repo.find_by_id(db, snippet_id)
        if not snippet:
            raise RecordNotFoundError("代码片段不存在")
        await self.repo.increment_use_count(db, snippet_id)
        updated = await self.repo.find_by_id(db, snippet_id)
        return self._serialize(updated)
