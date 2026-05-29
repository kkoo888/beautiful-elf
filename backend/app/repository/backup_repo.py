"""备份管理 Repository"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import BackupRecord


class BackupRepository:
    def __init__(self):
        self.mapper = MySQLMapper(BackupRecord)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[BackupRecord]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        backup_type: Optional[int] = None, status: Optional[int] = None,
    ) -> List[BackupRecord]:
        filters = {}
        if backup_type is not None:
            filters["backup_type"] = backup_type
        if status is not None:
            filters["status"] = status
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(
        self, db: AsyncSession,
        backup_type: Optional[int] = None, status: Optional[int] = None,
    ) -> int:
        filters = {}
        if backup_type is not None:
            filters["backup_type"] = backup_type
        if status is not None:
            filters["status"] = status
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> BackupRecord:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> bool:
        return await self.mapper.update(db, id, data)
