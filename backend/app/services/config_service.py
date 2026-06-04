"""配置管理 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.config_repo import ConfigRepository
from app.schemas.config import SettingCreate, SettingUpdate, SettingOut
from app.core.exceptions import RecordNotFoundError, DuplicateEntryError


class ConfigService:
    def __init__(self):
        self.repo = ConfigRepository()
        self._cache: dict = {}  # 内存缓存

    @staticmethod
    def _serialize(setting) -> dict:
        return SettingOut.model_validate(setting).model_dump()

    async def load_all(self, db: AsyncSession) -> None:
        """启动时加载全部配置到内存"""
        settings = await self.repo.find_all_active(db)
        self._cache = {s.settings_key: s.key_value for s in settings}

    async def get_by_key(self, db: AsyncSession, key: str) -> dict:
        setting = await self.repo.find_by_key(db, key)
        if not setting:
            raise RecordNotFoundError(f"配置 {key} 不存在")
        return self._serialize(setting)

    async def get_value(self, key: str) -> Optional[str]:
        """从内存缓存获取值（零延迟）"""
        return self._cache.get(key)

    async def list(self, db: AsyncSession, page: int = 1, page_size: int = 100) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size)
        total = await self.repo.count(db)
        return [self._serialize(s) for s in items], total

    async def create(self, db: AsyncSession, data: SettingCreate) -> dict:
        existing = await self.repo.find_by_key(db, data.settings_key)
        if existing:
            raise DuplicateEntryError(f"配置 {data.settings_key} 已存在")
        setting = await self.repo.create(db, data.model_dump())
        self._cache[setting.settings_key] = setting.key_value
        return self._serialize(setting)

    async def update(self, db: AsyncSession, key: str, data: SettingUpdate) -> dict:
        update_data = data.model_dump(exclude_unset=True)
        setting = await self.repo.update_by_key(db, key, update_data)
        if not setting:
            raise RecordNotFoundError(f"配置 {key} 不存在")
        self._cache[setting.settings_key] = setting.key_value
        return self._serialize(setting)

    async def delete(self, db: AsyncSession, key: str) -> bool:
        result = await self.repo.delete_by_key(db, key)
        if not result:
            raise RecordNotFoundError(f"配置 {key} 不存在")
        self._cache.pop(key, None)
        return True
