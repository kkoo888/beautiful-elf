"""命令使用统计 Repository"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import CommandUsage
from app.core.exceptions import StorageError


class CommandUsageRepository:
    def __init__(self):
        self.mapper = MySQLMapper(CommandUsage)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[CommandUsage]:
        return await self.mapper.find_by_id(db, id)

    async def find_by_command_id(self, db: AsyncSession, command_id: int) -> Optional[CommandUsage]:
        """按命令 ID 查询使用记录"""
        try:
            stmt = select(CommandUsage).where(
                CommandUsage.command_id == command_id,
                CommandUsage.is_deleted == 0,
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            raise StorageError(f"查询失败: {e}")

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20
    ) -> List[CommandUsage]:
        return await self.mapper.find_all(db, offset=offset, limit=limit)

    async def count(self, db: AsyncSession) -> int:
        return await self.mapper.count(db)

    async def create(self, db: AsyncSession, data: dict) -> CommandUsage:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[CommandUsage]:
        return await self.mapper.update(db, id, data)

    async def top_commands(self, db: AsyncSession, limit: int = 10) -> List[CommandUsage]:
        """按使用次数降序取 Top N"""
        try:
            stmt = (
                select(CommandUsage)
                .where(CommandUsage.is_deleted == 0)
                .order_by(CommandUsage.use_count.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise StorageError(f"查询 Top 命令失败: {e}")
