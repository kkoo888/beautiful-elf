"""配置管理 Repository"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import Setting


class ConfigRepository:
    """配置仓储 — settings 表"""

    def __init__(self):
        self.mapper = MySQLMapper(Setting)

    async def find_by_key(self, db: AsyncSession, key: str) -> Optional[Setting]:
        """按 key 查询配置"""
        stmt = select(Setting).where(
            Setting.settings_key == key,
            Setting.deleted == 0,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(self, db: AsyncSession, offset: int = 0, limit: int = 100) -> List[Setting]:
        """查询全部配置"""
        return await self.mapper.find_all(db, offset=offset, limit=limit)

    async def count(self, db: AsyncSession) -> int:
        return await self.mapper.count(db)

    async def create(self, db: AsyncSession, data: dict) -> Setting:
        return await self.mapper.create(db, data)

    async def update_by_key(self, db: AsyncSession, key: str, data: dict) -> Optional[Setting]:
        """按 key 更新配置"""
        setting = await self.find_by_key(db, key)
        if not setting:
            return None
        return await self.mapper.update(db, setting.id, data)

    async def delete_by_key(self, db: AsyncSession, key: str) -> bool:
        """按 key 软删除"""
        setting = await self.find_by_key(db, key)
        if not setting:
            return False
        return await self.mapper.soft_delete(db, setting.id)

    async def find_all_active(self, db: AsyncSession) -> List[Setting]:
        """查询所有未删除配置（用于启动加载）"""
        return await self.mapper.find_all(db, offset=0, limit=10000)
