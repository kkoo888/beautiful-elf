"""技能管理 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.skill_repo import SkillRepository
from app.schemas.skill import SkillCreate, SkillUpdate
from app.core.exceptions import RecordNotFoundError, DuplicateEntryError


class SkillService:
    def __init__(self):
        self.repo = SkillRepository()

    async def create(self, db: AsyncSession, data: SkillCreate) -> dict:
        existing = await self.repo.find_by_name(db, data.name)
        if existing:
            raise DuplicateEntryError(f"技能名称 '{data.name}' 已存在")
        item = await self.repo.create(db, data.model_dump())
        return self._to_dict(item)

    async def get_by_id(self, db: AsyncSession, id: int) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        return self._to_dict(item)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        enabled: Optional[int] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, enabled=enabled)
        total = await self.repo.count(db, enabled=enabled)
        return [self._to_dict(i) for i in items], total

    async def update(self, db: AsyncSession, id: int, data: SkillUpdate) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_dict(item)
        updated = await self.repo.update(db, id, update_data)
        return self._to_dict(updated)

    async def delete(self, db: AsyncSession, id: int) -> bool:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        return await self.repo.soft_delete(db, id)

    async def enable(self, db: AsyncSession, id: int) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        await self.repo.set_enabled(db, id, 1)
        updated = await self.repo.find_by_id(db, id)
        return self._to_dict(updated)

    async def disable(self, db: AsyncSession, id: int) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        await self.repo.set_enabled(db, id, 0)
        updated = await self.repo.find_by_id(db, id)
        return self._to_dict(updated)

    async def record_call(
        self, db: AsyncSession, skill_id: int, success: bool, duration_ms: int,
    ) -> dict:
        stats = await self.repo.record_call(db, skill_id, success, duration_ms)
        return self._stats_to_dict(stats)

    async def get_stats(self, db: AsyncSession, skill_id: int) -> dict:
        stats = await self.repo.get_stats(db, skill_id)
        if not stats:
            raise RecordNotFoundError("技能统计数据不存在")
        return self._stats_to_dict(stats)

    @staticmethod
    def _to_dict(item) -> dict:
        return {
            "id": item.id,
            "name": item.name,
            "display_name": item.display_name,
            "description": item.description,
            "version": item.version,
            "source": item.source,
            "trigger_words": item.trigger_words,
            "dependencies": item.dependencies,
            "isEnabled": item.is_enabled,
            "config": item.config,
            "created_at": str(item.created_at) if item.created_at else None,
            "updated_at": str(item.updated_at) if item.updated_at else None,
        }

    @staticmethod
    def _stats_to_dict(stats) -> dict:
        return {
            "id": stats.id,
            "skill_id": stats.skill_id,
            "call_count": stats.call_count,
            "success_count": stats.success_count,
            "fail_count": stats.fail_count,
            "avg_duration_ms": stats.avg_duration_ms,
            "last_called_at": str(stats.last_called_at) if stats.last_called_at else None,
        }
