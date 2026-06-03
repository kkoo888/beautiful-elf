"""命令使用统计 Service"""
from typing import List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.command_usage_repo import CommandUsageRepository


class CommandUsageService:
    def __init__(self):
        self.repo = CommandUsageRepository()

    async def record_use(self, db: AsyncSession, command_id: int) -> dict:
        """记录一次命令使用，自动 +1"""
        item = await self.repo.find_by_command_id(db, command_id)
        if item:
            updated = await self.repo.update(
                db, item.id,
                {"use_count": item.use_count + 1, "last_used_at": datetime.now()},
            )
            return self._to_dict(updated)
        else:
            created = await self.repo.create(db, {
                "command_id": command_id,
                "use_count": 1,
                "last_used_at": datetime.now(),
            })
            return self._to_dict(created)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size)
        total = await self.repo.count(db)
        return [self._to_dict(i) for i in items], total

    async def top_commands(self, db: AsyncSession, limit: int = 10) -> list:
        items = await self.repo.top_commands(db, limit)
        return [self._to_dict(i) for i in items]

    @staticmethod
    def _to_dict(item) -> dict:
        return {
            "id": item.id,
            "commandId": item.command_id,
            "useCount": item.use_count,
            "lastUsedAt": str(item.last_used_at) if item.last_used_at else None,
            "createdAt": str(item.created_at) if item.created_at else None,
            "updatedAt": str(item.updated_at) if item.updated_at else None,
        }
