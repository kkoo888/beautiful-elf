"""备份管理 Service"""
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.backup_repo import BackupRepository
from app.schemas.backup import BackupCreate, BackupStatusUpdate, BackupOut
from app.core.exceptions import RecordNotFoundError


class BackupService:
    def __init__(self):
        self.repo = BackupRepository()

    @staticmethod
    def _serialize(item) -> dict:
        return BackupOut.model_validate(item).model_dump(by_alias=True)

    async def create(self, db: AsyncSession, data: BackupCreate) -> dict:
        item = await self.repo.create(db, data.model_dump())
        return self._serialize(item)

    async def get_by_id(self, db: AsyncSession, id: int) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("备份记录不存在")
        return self._serialize(item)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        backup_type: Optional[int] = None, status: Optional[int] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(
            db, offset=offset, limit=page_size,
            backup_type=backup_type, status=status,
        )
        total = await self.repo.count(db, backup_type=backup_type, status=status)
        return [self._serialize(i) for i in items], total

    async def update_status(self, db: AsyncSession, id: int, data: BackupStatusUpdate) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("备份记录不存在")
        update_data = data.model_dump(exclude_unset=True)
        await self.repo.update(db, id, update_data)
        updated = await self.repo.find_by_id(db, id)
        return self._serialize(updated)
