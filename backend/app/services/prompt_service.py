"""Prompt 版本管理 Service"""
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.prompt_repo import PromptRepository
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptOut
from app.core.exceptions import RecordNotFoundError


class PromptService:
    def __init__(self):
        self.repo = PromptRepository()

    async def create(self, db: AsyncSession, data: PromptCreate) -> dict:
        max_ver = await self.repo.get_max_version(db, data.name)
        new_data = data.model_dump()
        new_data["version"] = max_ver + 1
        new_data["is_active"] = 0
        item = await self.repo.create(db, new_data)
        return self._to_dict(item)

    async def get_by_id(self, db: AsyncSession, id: int) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("Prompt 不存在")
        return self._to_dict(item)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        name: Optional[str] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, name=name)
        total = await self.repo.count(db, name=name)
        return [self._to_dict(i) for i in items], total

    async def update(self, db: AsyncSession, id: int, data: PromptUpdate) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("Prompt 不存在")
        update_data = data.model_dump(exclude_unset=True)
        await self.repo.update(db, id, update_data)
        updated = await self.repo.find_by_id(db, id)
        return self._to_dict(updated)

    async def delete(self, db: AsyncSession, id: int) -> bool:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("Prompt 不存在")
        return await self.repo.soft_delete(db, id)

    async def activate(self, db: AsyncSession, id: int) -> dict:
        """激活某个版本，同时把同名其他版本 is_active 设为 0"""
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("Prompt 不存在")
        # 先把同名所有版本设为未激活
        await self.repo.deactivate_by_name(db, item.name)
        # 再激活当前版本
        await self.repo.update(db, id, {"is_active": 1})
        updated = await self.repo.find_by_id(db, id)
        return self._to_dict(updated)

    async def get_active(self, db: AsyncSession, name: str) -> Optional[dict]:
        """获取某个 name 当前激活的版本"""
        item = await self.repo.find_active_by_name(db, name)
        if not item:
            return None
        return self._to_dict(item)

    async def get_versions(self, db: AsyncSession, name: str) -> list:
        """获取某个 name 的所有版本列表"""
        items = await self.repo.find_versions_by_name(db, name)
        return [self._to_dict(i) for i in items]

    @staticmethod
    def _to_dict(item) -> dict:
        return PromptOut.model_validate(item).model_dump()
