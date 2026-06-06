"""Prompt 版本管理 Repository"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import Prompt


class PromptRepository:
    def __init__(self):
        self.mapper = MySQLMapper(Prompt)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Prompt]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        name: Optional[str] = None,
    ) -> List[Prompt]:
        filters = {}
        if name:
            filters["name"] = name
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, name: Optional[str] = None) -> int:
        filters = {}
        if name:
            filters["name"] = name
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> Prompt:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> bool:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def get_max_version(self, db: AsyncSession, name: str) -> int:
        """获取某个 name 的最大版本号"""
        stmt = select(func.coalesce(func.max(Prompt.version), 0)).where(
            Prompt.name == name, Prompt.is_deleted == 0
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def find_active_by_name(self, db: AsyncSession, name: str) -> Optional[Prompt]:
        """获取某个 name 当前激活的版本"""
        stmt = select(Prompt).where(
            Prompt.name == name, Prompt.is_active == 1, Prompt.is_deleted == 0
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def deactivate_by_name(self, db: AsyncSession, name: str) -> int:
        """将某个 name 的所有版本设为未激活"""
        from sqlalchemy import update as sa_update
        stmt = (
            sa_update(Prompt)
            .where(Prompt.name == name, Prompt.is_active == 1, Prompt.is_deleted == 0)
            .values(is_active=0)
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount

    async def find_versions_by_name(self, db: AsyncSession, name: str) -> List[Prompt]:
        """获取某个 name 的所有版本列表"""
        stmt = (
            select(Prompt)
            .where(Prompt.name == name, Prompt.is_deleted == 0)
            .order_by(Prompt.version.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
