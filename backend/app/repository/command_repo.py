"""命令面板 Repository"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import Command, CommandUsage


class CommandRepository:
    def __init__(self):
        self.mapper = MySQLMapper(Command)
        self.usage_mapper = MySQLMapper(CommandUsage)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Command]:
        return await self.mapper.find_by_id(db, id)

    async def find_by_name(self, db: AsyncSession, name: str) -> Optional[Command]:
        stmt = select(Command).where(Command.name == name, Command.deleted == 0)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        module: Optional[str] = None,
    ) -> List[Command]:
        filters = {}
        if module:
            filters["module"] = module
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession) -> int:
        return await self.mapper.count(db)

    async def create(self, db: AsyncSession, data: dict) -> Command:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[Command]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def record_usage(self, db: AsyncSession, command_id: int) -> None:
        """记录命令使用（更新或创建 usage 记录）"""
        stmt = select(CommandUsage).where(
            CommandUsage.command_id == command_id, CommandUsage.deleted == 0
        )
        result = await db.execute(stmt)
        usage = result.scalar_one_or_none()
        if usage:
            await self.usage_mapper.update(db, usage.id, {
                "use_count": usage.use_count + 1,
                "last_used_at": func.now(),
            })
        else:
            await self.usage_mapper.create(db, {
                "command_id": command_id,
                "use_count": 1,
            })
