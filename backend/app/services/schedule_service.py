"""日程管理 Service"""
from typing import List, Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.schedule_repo import ScheduleRepository
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleOut
from app.core.exceptions import RecordNotFoundError


class ScheduleService:
    def __init__(self):
        self.repo = ScheduleRepository()

    @staticmethod
    def _to_out(s) -> ScheduleOut:
        """ORM → Pydantic 模型"""
        return ScheduleOut.model_validate(s)

    async def create_schedule(self, db: AsyncSession, data: ScheduleCreate) -> ScheduleOut:
        schedule = await self.repo.create(db, data.model_dump())
        return self._to_out(schedule)

    async def get_schedule_by_id(self, db: AsyncSession, schedule_id: int) -> ScheduleOut:
        schedule = await self.repo.find_by_id(db, schedule_id)
        if not schedule:
            raise RecordNotFoundError("日程不存在")
        return self._to_out(schedule)

    async def list_schedules(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
    ) -> Tuple[List[ScheduleOut], int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, start_time=start_time, end_time=end_time)
        total = await self.repo.count(db, start_time=start_time, end_time=end_time)
        return [self._to_out(s) for s in items], total

    async def update_schedule(self, db: AsyncSession, schedule_id: int, data: ScheduleUpdate) -> ScheduleOut:
        existing = await self.repo.find_by_id(db, schedule_id)
        if not existing:
            raise RecordNotFoundError("日程不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_out(existing)
        schedule = await self.repo.update(db, schedule_id, update_data)
        return self._to_out(schedule)

    async def delete_schedule(self, db: AsyncSession, schedule_id: int) -> bool:
        existing = await self.repo.find_by_id(db, schedule_id)
        if not existing:
            raise RecordNotFoundError("日程不存在")
        return await self.repo.soft_delete(db, schedule_id)
