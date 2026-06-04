"""大模型供应商 Service"""
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.llm_provider_repo import LLMProviderRepository
from app.schemas.llm_provider import ProviderCreate, ProviderUpdate, ProviderOut
from app.core.exceptions import RecordNotFoundError


class LLMProviderService:
    def __init__(self):
        self.repo = LLMProviderRepository()

    async def list(self, db: AsyncSession, page: int = 1, page_size: int = 20) -> Tuple[List[ProviderOut], int]:
        """供应商列表（分页）"""
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size)
        total = await self.repo.count(db)
        return [self._to_out(p) for p in items], total

    async def list_enabled(self, db: AsyncSession) -> List[ProviderOut]:
        """获取所有启用的供应商（用于前端模型选择）"""
        items = await self.repo.find_enabled(db)
        return [self._to_out(p) for p in items]

    async def get(self, db: AsyncSession, provider_id: int) -> ProviderOut:
        """获取单个供应商"""
        provider = await self.repo.find_by_id(db, provider_id)
        if not provider:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")
        return self._to_out(provider)

    async def create(self, db: AsyncSession, data: ProviderCreate) -> ProviderOut:
        """创建供应商"""
        # 如果设为默认，先清除其他默认
        if data.is_default == 1:
            await self.repo.clear_default(db)

        provider = await self.repo.create(db, data.model_dump())
        return self._to_out(provider)

    async def update(self, db: AsyncSession, provider_id: int, data: ProviderUpdate) -> ProviderOut:
        """更新供应商"""
        existing = await self.repo.find_by_id(db, provider_id)
        if not existing:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")

        update_data = data.model_dump(exclude_unset=True)

        # 如果设为默认，先清除其他默认
        if update_data.get("is_default") == 1:
            await self.repo.clear_default(db)

        provider = await self.repo.update(db, provider_id, update_data)
        return self._to_out(provider)

    async def toggle_enabled(self, db: AsyncSession, provider_id: int) -> ProviderOut:
        """切换启用/禁用状态"""
        existing = await self.repo.find_by_id(db, provider_id)
        if not existing:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")

        new_enabled = 0 if existing.is_enabled == 1 else 1
        provider = await self.repo.update(db, provider_id, {"is_enabled": new_enabled})
        return self._to_out(provider)

    async def delete(self, db: AsyncSession, provider_id: int) -> bool:
        """删除供应商"""
        result = await self.repo.soft_delete(db, provider_id)
        if not result:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")
        return True

    @staticmethod
    def _to_out(provider) -> ProviderOut:
        """ORM → Pydantic 模型"""
        return ProviderOut.model_validate(provider)
