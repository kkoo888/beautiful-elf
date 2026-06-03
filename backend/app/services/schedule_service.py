"""日程管理 Service"""
from typing import List, Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.schedule_repo import ScheduleRepository
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.core.exceptions import RecordNotFoundError


class ScheduleService:
    def __init__(self):
        self.repo = ScheduleRepository()

    async def create(self, db: AsyncSession, data: ScheduleCreate) -> dict:
        schedule = await self.repo.create(db, data.model_dump())
        return self._to_dict(schedule)

    async def get_by_id(self, db: AsyncSession, schedule_id: int) -> dict:
        schedule = await self.repo.find_by_id(db, schedule_id)
        if not schedule:
            raise RecordNotFoundError("日程不存在")
        return self._to_dict(schedule)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, start_time=start_time, end_time=end_time)
        total = await self.repo.count(db, start_time=start_time, end_time=end_time)
        return [self._to_dict(s) for s in items], total

    async def update(self, db: AsyncSession, schedule_id: int, data: ScheduleUpdate) -> dict:
        existing = await self.repo.find_by_id(db, schedule_id)
        if not existing:
            raise RecordNotFoundError("日程不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_dict(existing)
        schedule = await self.repo.update(db, schedule_id, update_data)
        return self._to_dict(schedule)

    async def delete(self, db: AsyncSession, schedule_id: int) -> bool:
        existing = await self.repo.find_by_id(db, schedule_id)
        if not existing:
            raise RecordNotFoundError("日程不存在")
        return await self.repo.soft_delete(db, schedule_id)

    @staticmethod
    def _to_dict(s) -> dict:
        return {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "startTime": str(s.start_time) if s.start_time else None,
            "endTime": str(s.end_time) if s.end_time else None,
            "isAllDay": s.is_all_day,
            "reminderMinutes": s.reminder_minutes,
            "isReminded": s.is_reminded,
            "repeatType": s.repeat_type,
            "color": s.color,
            "createdAt": str(s.created_at) if s.created_at else None,
            "updatedAt": str(s.updated_at) if s.updated_at else None,
        }
