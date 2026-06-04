"""剪贴板 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.clipboard_repo import ClipboardRepository
from app.schemas.clipboard import ClipboardItemCreate, ClipboardItemUpdate, ClipboardItemOut
from app.core.exceptions import RecordNotFoundError


class ClipboardService:
    def __init__(self):
        self.repo = ClipboardRepository()

    @staticmethod
    def _to_out(item) -> ClipboardItemOut:
        """ORM → Pydantic 模型"""
        return ClipboardItemOut.model_validate(item)

    async def create(self, db: AsyncSession, data: ClipboardItemCreate) -> ClipboardItemOut:
        item = await self.repo.create(db, data.model_dump())
        return self._to_out(item)

    async def get_by_id(self, db: AsyncSession, item_id: int) -> ClipboardItemOut:
        item = await self.repo.find_by_id(db, item_id)
        if not item:
            raise RecordNotFoundError("剪贴板项不存在")
        return self._to_out(item)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        content_type: Optional[int] = None, pinned: Optional[int] = None,
    ) -> Tuple[List[ClipboardItemOut], int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, content_type=content_type, pinned=pinned)
        total = await self.repo.count(db, content_type=content_type)
        return [self._to_out(i) for i in items], total

    async def update(self, db: AsyncSession, item_id: int, data: ClipboardItemUpdate) -> ClipboardItemOut:
        existing = await self.repo.find_by_id(db, item_id)
        if not existing:
            raise RecordNotFoundError("剪贴板项不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_out(existing)
        item = await self.repo.update(db, item_id, update_data)
        return self._to_out(item)

    async def delete(self, db: AsyncSession, item_id: int) -> bool:
        existing = await self.repo.find_by_id(db, item_id)
        if not existing:
            raise RecordNotFoundError("剪贴板项不存在")
        return await self.repo.soft_delete(db, item_id)

    async def toggle_pin(self, db: AsyncSession, item_id: int) -> ClipboardItemOut:
        item = await self.repo.toggle_pin(db, item_id)
        if not item:
            raise RecordNotFoundError("剪贴板项不存在")
        return self._to_out(item)
