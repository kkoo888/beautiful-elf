"""日程管理 Repository"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import Schedule


class ScheduleRepository:
    """日程仓储 — schedules 表"""

    def __init__(self):
        self.mapper = MySQLMapper(Schedule)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Schedule]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Schedule]:
        """分页查询，支持时间范围过滤"""
        stmt = select(Schedule).where(Schedule.deleted == 0)
        if start_time:
            stmt = stmt.where(Schedule.start_time >= start_time)
        if end_time:
            stmt = stmt.where(Schedule.start_time <= end_time)
        stmt = stmt.order_by(Schedule.start_time.asc())
        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        db: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        count_stmt = select(func.count()).select_from(Schedule).where(Schedule.deleted == 0)
        if start_time:
            count_stmt = count_stmt.where(Schedule.start_time >= start_time)
        if end_time:
            count_stmt = count_stmt.where(Schedule.start_time <= end_time)
        result = await db.execute(count_stmt)
        return result.scalar() or 0

    async def create(self, db: AsyncSession, data: dict) -> Schedule:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[Schedule]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)
