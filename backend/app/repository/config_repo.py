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
            Setting.is_deleted == 0,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(self, db: AsyncSession, offset: int = 0, limit: int = 100) -> List[Setting]:
        """查询全部配置"""
        return await self.mapper.find_all(db, offset=offset, limit=limit)

    async def count(self, db: AsyncSession) -> int:
        return await self.mapper.count(db)

    async def create(self, db: AsyncSession, data: dict) -> Setting:
        """创建配置，如果已存在（含软删除）则恢复并更新"""
        # 检查是否有同名记录（含软删除）
        stmt = select(Setting).where(Setting.settings_key == data.get('settings_key', ''))
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            # 已存在（可能被软删除），直接更新所有字段 + 恢复
            from sqlalchemy import update as sa_update
            update_stmt = (
                sa_update(Setting)
                .where(Setting.id == existing.id)
                .values(**data, is_deleted=0)
            )
            await db.execute(update_stmt)
            await db.flush()
            return await self.find_by_key(db, data.get('settings_key', ''))
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
