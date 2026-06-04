"""备份管理 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.backup_repo import BackupRepository
from app.schemas.backup import BackupCreate, BackupStatusUpdate, BackupOut
from app.core.exceptions import RecordNotFoundError


class BackupService:
    def __init__(self):
        self.repo = BackupRepository()

    @staticmethod
    def _to_out(item) -> BackupOut:
        """ORM → Pydantic 模型"""
        return BackupOut.model_validate(item)

    async def create(self, db: AsyncSession, data: BackupCreate) -> BackupOut:
        item = await self.repo.create(db, data.model_dump())
        return self._to_out(item)

    async def get_by_id(self, db: AsyncSession, id: int) -> BackupOut:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("备份记录不存在")
        return self._to_out(item)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        backup_type: Optional[int] = None, status: Optional[int] = None,
    ) -> Tuple[List[BackupOut], int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(
            db, offset=offset, limit=page_size,
            backup_type=backup_type, status=status,
        )
        total = await self.repo.count(db, backup_type=backup_type, status=status)
        return [self._to_out(i) for i in items], total

    async def update_status(self, db: AsyncSession, id: int, data: BackupStatusUpdate) -> BackupOut:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("备份记录不存在")
        update_data = data.model_dump(exclude_unset=True)
        await self.repo.update(db, id, update_data)
        updated = await self.repo.find_by_id(db, id)
        return self._to_out(updated)
