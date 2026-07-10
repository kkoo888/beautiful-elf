"""工具审批白名单 Repository"""
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.tool_approval import ToolApprovalWhitelist


class ToolApprovalWhitelistRepository:
    """工具审批白名单 CRUD"""

    def __init__(self):
        self.mapper = MySQLMapper(ToolApprovalWhitelist)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[ToolApprovalWhitelist]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        user_id: int = 0, tool_name: str = "",
    ) -> List[ToolApprovalWhitelist]:
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if tool_name:
            filters["tool_name"] = tool_name
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, user_id: int = 0, tool_name: str = "") -> int:
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if tool_name:
            filters["tool_name"] = tool_name
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> ToolApprovalWhitelist:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> None:
        await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> None:
        await self.mapper.update(db, id, {"is_deleted": 1})

    async def find_match(
        self,
        db: AsyncSession,
        user_id: int,
        tool_name: str,
        path: str,
        command: str = "",
    ) -> Optional[ToolApprovalWhitelist]:
        """查找匹配的白名单记录

        匹配逻辑：
          1. tool_name 精确匹配
          2. path 以 path_pattern 开头（前缀匹配）
          3. command 包含 command_pattern（子串匹配，空 pattern = 全部放行）
        """
        stmt = (
            select(ToolApprovalWhitelist)
            .where(
                and_(
                    ToolApprovalWhitelist.user_id == user_id,
                    ToolApprovalWhitelist.tool_name == tool_name,
                    ToolApprovalWhitelist.is_deleted == 0,
                )
            )
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        for row in rows:
            # 路径前缀匹配（空 pattern = 全部放行）
            if row.path_pattern and not path.startswith(row.path_pattern):
                continue
            # 命令子串匹配（空 pattern = 全部放行）
            if row.command_pattern and row.command_pattern not in command:
                continue
            return row

        return None

    async def increment_hit(self, db: AsyncSession, record_id: int) -> None:
        """增加命中次数"""
        record = await self.find_by_id(db, record_id)
        if record:
            await self.mapper.update(db, record_id, {"hit_count": record.hit_count + 1})
