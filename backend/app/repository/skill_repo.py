"""技能管理 Repository"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import Skill, SkillStats


class SkillRepository:
    def __init__(self):
        self.mapper = MySQLMapper(Skill)
        self.stats_mapper = MySQLMapper(SkillStats)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Skill]:
        return await self.mapper.find_by_id(db, id)

    async def find_by_name(self, db: AsyncSession, name: str) -> Optional[Skill]:
        stmt = select(Skill).where(Skill.name == name, Skill.deleted == 0)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        enabled: Optional[int] = None,
    ) -> List[Skill]:
        filters = {}
        if enabled is not None:
            filters["enabled"] = enabled
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, enabled: Optional[int] = None) -> int:
        filters = {}
        if enabled is not None:
            filters["enabled"] = enabled
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> Skill:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[Skill]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def set_enabled(self, db: AsyncSession, id: int, enabled: int) -> bool:
        stmt = (
            update(Skill)
            .where(Skill.id == id, Skill.deleted == 0)
            .values(enabled=enabled)
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount > 0

    async def get_stats(self, db: AsyncSession, skill_id: int) -> Optional[SkillStats]:
        stmt = select(SkillStats).where(SkillStats.skill_id == skill_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def record_call(
        self, db: AsyncSession, skill_id: int, success: bool, duration_ms: int,
    ) -> SkillStats:
        stats = await self.get_stats(db, skill_id)
        if not stats:
            data = {
                "skill_id": skill_id,
                "call_count": 1,
                "success_count": 1 if success else 0,
                "fail_count": 0 if success else 1,
                "avg_duration_ms": duration_ms,
                "last_called_at": datetime.now(),
            }
            return await self.stats_mapper.create(db, data)
        new_call_count = stats.call_count + 1
        new_success = stats.success_count + (1 if success else 0)
        new_fail = stats.fail_count + (0 if success else 1)
        new_avg = int((stats.avg_duration_ms * stats.call_count + duration_ms) / new_call_count)
        stmt = (
            update(SkillStats)
            .where(SkillStats.id == stats.id)
            .values(
                call_count=new_call_count,
                success_count=new_success,
                fail_count=new_fail,
                avg_duration_ms=new_avg,
                last_called_at=datetime.now(),
            )
        )
        await db.execute(stmt)
        await db.flush()
        return await self.stats_mapper.find_by_id(db, stats.id)
