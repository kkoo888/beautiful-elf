"""通知系统 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.notification_repo import NotificationRepository
from app.schemas.notification import NotificationCreate, NotificationOut
from app.core.exceptions import RecordNotFoundError


class NotificationService:
    def __init__(self):
        self.repo = NotificationRepository()

    async def create(self, db: AsyncSession, data: NotificationCreate) -> dict:
        notif = await self.repo.create(db, data.model_dump())
        return self._to_dict(notif)

    async def get_by_id(self, db: AsyncSession, notif_id: int) -> dict:
        notif = await self.repo.find_by_id(db, notif_id)
        if not notif:
            raise RecordNotFoundError("通知不存在")
        return self._to_dict(notif)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        notif_type: Optional[str] = None, read_status: Optional[int] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(
            db, offset=offset, limit=page_size, type_=notif_type, read=read_status,
        )
        total = await self.repo.count(db, read=read_status)
        return [self._to_dict(n) for n in items], total

    async def delete(self, db: AsyncSession, notif_id: int) -> bool:
        notif = await self.repo.find_by_id(db, notif_id)
        if not notif:
            raise RecordNotFoundError("通知不存在")
        return await self.repo.soft_delete(db, notif_id)

    async def mark_read(self, db: AsyncSession, notif_id: int) -> dict:
        notif = await self.repo.find_by_id(db, notif_id)
        if not notif:
            raise RecordNotFoundError("通知不存在")
        await self.repo.mark_read(db, notif_id)
        updated = await self.repo.find_by_id(db, notif_id)
        return self._to_dict(updated)

    async def mark_all_read(self, db: AsyncSession) -> int:
        return await self.repo.mark_all_read(db)

    @staticmethod
    def _to_dict(notif) -> dict:
        return NotificationOut.model_validate(notif).model_dump(by_alias=True)
