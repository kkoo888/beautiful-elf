"""记忆设置 Repository"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.memory_setting import MemorySetting


class MemorySettingRepository:
    """记忆设置仓储 — memory_setting 表"""

    def __init__(self):
        self.mapper = MySQLMapper(MemorySetting)

    async def find_by_key(self, db: AsyncSession, key: str) -> Optional[MemorySetting]:
        """按 key 查询"""
        stmt = select(MemorySetting).where(
            MemorySetting.setting_key == key,
            MemorySetting.is_deleted == 0,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_by_key(self, db: AsyncSession, key: str, is_enabled: int) -> MemorySetting:
        """存在则更新 is_enabled，不存在则创建"""
        setting = await self.find_by_key(db, key)
        if setting:
            return await self.mapper.update(db, setting.id, {"is_enabled": is_enabled})
        return await self.mapper.create(db, {"setting_key": key, "is_enabled": is_enabled})

    async def find_all_scheduler_settings(self, db: AsyncSession) -> List[MemorySetting]:
        """查询所有 scheduler_ 前缀的设置"""
        stmt = select(MemorySetting).where(
            MemorySetting.setting_key.like("scheduler_%"),
            MemorySetting.is_deleted == 0,
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_model_setting(self, db: AsyncSession, key: str, provider_id: int, model_name: str) -> Optional[MemorySetting]:
        """更新指定 key 的 provider_id 和 model_name"""
        setting = await self.find_by_key(db, key)
        if setting:
            return await self.mapper.update(db, setting.id, {"provider_id": provider_id, "model_name": model_name})
        return None

    async def create_with_model(self, db: AsyncSession, key: str, provider_id: int, model_name: str) -> MemorySetting:
        """创建带 provider_id 和 model_name 的设置"""
        return await self.mapper.create(db, {"setting_key": key, "provider_id": provider_id, "model_name": model_name})

    async def get_model_setting(self, db: AsyncSession, key: str) -> tuple[int, str]:
        """获取指定 key 的 provider_id 和 model_name，不存在返回 (0, "")"""
        setting = await self.find_by_key(db, key)
        if setting:
            return setting.provider_id, setting.model_name
        return 0, ""
