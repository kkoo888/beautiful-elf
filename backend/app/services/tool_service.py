"""工具管理 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.tool_repo import ToolRepository
from app.schemas.tool import ToolCreate, ToolUpdate, ToolOut, ToolStatsOut
from app.core.exceptions import RecordNotFoundError, DuplicateEntryError


class ToolService:
    def __init__(self):
        self.repo = ToolRepository()

    async def create(self, db: AsyncSession, data: ToolCreate) -> ToolOut:
        existing = await self.repo.find_by_name(db, data.name)
        if existing:
            raise DuplicateEntryError(f"工具名称 '{data.name}' 已存在")
        item = await self.repo.create(db, data.model_dump())
        return self._to_out(item)

    async def get_by_id(self, db: AsyncSession, id: int) -> ToolOut:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("工具不存在")
        return self._to_out(item)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        enabled: Optional[int] = None,
    ) -> Tuple[List[ToolOut], int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, enabled=enabled)
        total = await self.repo.count(db, enabled=enabled)
        return [self._to_out(i) for i in items], total

    async def update(self, db: AsyncSession, id: int, data: ToolUpdate) -> ToolOut:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("工具不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_out(item)
        updated = await self.repo.update(db, id, update_data)
        return self._to_out(updated)

    async def delete(self, db: AsyncSession, id: int) -> bool:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("工具不存在")
        return await self.repo.soft_delete(db, id)

    async def enable(self, db: AsyncSession, id: int) -> ToolOut:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("工具不存在")
        await self.repo.set_enabled(db, id, 1)
        updated = await self.repo.find_by_id(db, id)
        return self._to_out(updated)

    async def disable(self, db: AsyncSession, id: int) -> ToolOut:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("工具不存在")
        await self.repo.set_enabled(db, id, 0)
        updated = await self.repo.find_by_id(db, id)
        return self._to_out(updated)

    async def record_call(
        self, db: AsyncSession, tool_id: int, success: bool, duration_ms: int,
    ) -> ToolStatsOut:
        stats = await self.repo.record_call(db, tool_id, success, duration_ms)
        return self._stats_to_out(stats)

    async def get_stats(self, db: AsyncSession, tool_id: int) -> ToolStatsOut:
        stats = await self.repo.get_stats(db, tool_id)
        if not stats:
            raise RecordNotFoundError("工具统计数据不存在")
        return self._stats_to_out(stats)

    @staticmethod
    def _to_out(item) -> ToolOut:
        """ORM → Pydantic 模型"""
        return ToolOut.model_validate(item)

    @staticmethod
    def _stats_to_out(stats) -> ToolStatsOut:
        """ORM → Pydantic 模型"""
        return ToolStatsOut.model_validate(stats)
