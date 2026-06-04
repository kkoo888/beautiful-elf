"""大模型供应商 Service"""
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.llm_provider_repo import LLMProviderRepository
from app.schemas.llm_provider import ProviderCreate, ProviderUpdate, ProviderOut
from app.core.exceptions import RecordNotFoundError


class LLMProviderService:
    def __init__(self):
        self.repo = LLMProviderRepository()

    async def list(self, db: AsyncSession, page: int = 1, page_size: int = 20) -> Tuple[list, int]:
        """供应商列表（分页）"""
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size)
        total = await self.repo.count(db)
        return [self._to_dict(p) for p in items], total

    async def list_enabled(self, db: AsyncSession) -> List[dict]:
        """获取所有启用的供应商（用于前端模型选择）"""
        items = await self.repo.find_enabled(db)
        return [self._to_dict(p) for p in items]

    async def get(self, db: AsyncSession, provider_id: int) -> dict:
        """获取单个供应商（camelCase，API 响应用）"""
        provider = await self.repo.find_by_id(db, provider_id)
        if not provider:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")
        return self._to_dict(provider)

    async def get_internal(self, db: AsyncSession, provider_id: int) -> dict:
        """获取单个供应商（snake_case，内部服务调用用）"""
        provider = await self.repo.find_by_id(db, provider_id)
        if not provider:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")
        return self._to_internal_dict(provider)

    async def create(self, db: AsyncSession, data: ProviderCreate) -> dict:
        """创建供应商"""
        # 如果设为默认，先清除其他默认
        if data.is_default == 1:
            await self.repo.clear_default(db)

        provider = await self.repo.create(db, data.model_dump())
        return self._to_dict(provider)

    async def update(self, db: AsyncSession, provider_id: int, data: ProviderUpdate) -> dict:
        """更新供应商"""
        existing = await self.repo.find_by_id(db, provider_id)
        if not existing:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")

        update_data = data.model_dump(exclude_unset=True)

        # 如果设为默认，先清除其他默认
        if update_data.get("is_default") == 1:
            await self.repo.clear_default(db)

        provider = await self.repo.update(db, provider_id, update_data)
        return self._to_dict(provider)

    async def toggle_enabled(self, db: AsyncSession, provider_id: int) -> dict:
        """切换启用/禁用状态"""
        existing = await self.repo.find_by_id(db, provider_id)
        if not existing:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")

        new_enabled = 0 if existing.is_enabled == 1 else 1
        provider = await self.repo.update(db, provider_id, {"is_enabled": new_enabled})
        return self._to_dict(provider)

    async def delete(self, db: AsyncSession, provider_id: int) -> bool:
        """删除供应商"""
        result = await self.repo.soft_delete(db, provider_id)
        if not result:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")
        return True

    def _to_dict(self, provider) -> dict:
        """转换为输出字典（camelCase）— 给 API 响应用"""
        return ProviderOut.model_validate(provider).model_dump(by_alias=True)

    def _to_internal_dict(self, provider) -> dict:
        """转换为内部字典（snake_case）— 给服务间调用用"""
        return ProviderOut.model_validate(provider).model_dump()
