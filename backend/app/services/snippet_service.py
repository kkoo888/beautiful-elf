"""代码片段 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.snippet_repo import SnippetRepository
from app.schemas.snippet import SnippetCreate, SnippetUpdate
from app.core.exceptions import RecordNotFoundError


class SnippetService:
    def __init__(self):
        self.repo = SnippetRepository()

    async def create(self, db: AsyncSession, data: SnippetCreate) -> dict:
        snippet_data = data.model_dump(exclude={"tags"})
        snippet = await self.repo.create(db, snippet_data, tags=data.tags)
        result = self._to_dict(snippet)
        result["tags"] = data.tags or []
        return result

    async def get_by_id(self, db: AsyncSession, snippet_id: int) -> dict:
        snippet = await self.repo.find_by_id(db, snippet_id)
        if not snippet:
            raise RecordNotFoundError("代码片段不存在")
        result = self._to_dict(snippet)
        result["tags"] = await self.repo.get_tags(db, snippet_id)
        return result

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        language: Optional[str] = None, tag: Optional[str] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, language=language, tag=tag)
        total = await self.repo.count(db)
        result = []
        for s in items:
            d = self._to_dict(s)
            d["tags"] = await self.repo.get_tags(db, s.id)
            result.append(d)
        return result, total

    async def update(self, db: AsyncSession, snippet_id: int, data: SnippetUpdate) -> dict:
        existing = await self.repo.find_by_id(db, snippet_id)
        if not existing:
            raise RecordNotFoundError("代码片段不存在")
        update_data = data.model_dump(exclude_unset=True, exclude={"tags"})
        tags = data.tags if data.tags is not None else None
        snippet = await self.repo.update(db, snippet_id, update_data, tags=tags)
        result = self._to_dict(snippet)
        result["tags"] = await self.repo.get_tags(db, snippet_id)
        return result

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
        return self._to_dict(updated)

    @staticmethod
    def _to_dict(s) -> dict:
        return {
            "id": s.id,
            "title": s.title,
            "content": s.content,
            "language": s.language,
            "use_count": s.use_count,
            "created_at": str(s.created_at) if s.created_at else None,
            "updated_at": str(s.updated_at) if s.updated_at else None,
        }
