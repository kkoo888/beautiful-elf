"""大模型供应商 + 模型 Service — 方案 A: 两表联动"""
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.llm_provider_repo import LLMProviderRepository
from app.repository.llm_model_repo import LLMModelRepository
from app.schemas.llm_provider import (
    ProviderCreate, ProviderUpdate, ProviderOut,
    LLMModelCreate, LLMModelUpdate, LLMModelOut,
)
from app.core.exceptions import RecordNotFoundError


class LLMProviderService:
    def __init__(self):
        self.provider_repo = LLMProviderRepository()
        self.model_repo = LLMModelRepository()

    # ── 供应商 CRUD ─────────────────────────────────────────

    async def list_providers(self, db: AsyncSession, page: int = 1, page_size: int = 20) -> Tuple[List[ProviderOut], int]:
        """供应商列表（分页，含模型列表）"""
        offset = (page - 1) * page_size
        providers = await self.provider_repo.find_all(db, offset=offset, limit=page_size)
        total = await self.provider_repo.count(db)
        result = []
        for p in providers:
            models = await self.model_repo.find_by_provider(db, p.id)
            result.append(self._to_provider_out(p, models))
        return result, total

    async def list_enabled_providers(self, db: AsyncSession) -> List[ProviderOut]:
        """获取所有启用的供应商（含启用模型）"""
        providers = await self.provider_repo.find_enabled(db)
        result = []
        for p in providers:
            models = await self.model_repo.find_enabled_by_provider(db, p.id)
            result.append(self._to_provider_out(p, models))
        return result

    async def get_provider(self, db: AsyncSession, provider_id: int) -> ProviderOut:
        """获取单个供应商（含模型）"""
        provider = await self.provider_repo.find_by_id(db, provider_id)
        if not provider:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")
        models = await self.model_repo.find_by_provider(db, provider_id)
        return self._to_provider_out(provider, models)

    async def get_default_provider(self, db: AsyncSession) -> Optional[ProviderOut]:
        """获取默认供应商"""
        provider = await self.provider_repo.find_default(db)
        if not provider:
            return None
        models = await self.model_repo.find_enabled_by_provider(db, provider.id)
        return self._to_provider_out(provider, models)

    async def create_provider(self, db: AsyncSession, data: ProviderCreate) -> ProviderOut:
        """创建供应商（可附带模型列表）"""
        if data.is_default == 1:
            await self.provider_repo.clear_default(db)

        provider = await self.provider_repo.create(db, {
            "name": data.name,
            "provider_type": data.provider_type,
            "base_url": data.base_url,
            "api_key": data.api_key,
            "is_enabled": data.is_enabled,
            "is_default": data.is_default,
            "description": data.description,
        })

        models = []
        if data.models:
            models = await self.model_repo.batch_create(
                db, provider.id, [m.model_dump() for m in data.models]
            )

        return self._to_provider_out(provider, models)

    async def update_provider(self, db: AsyncSession, provider_id: int, data: ProviderUpdate) -> ProviderOut:
        """更新供应商（models 传入时全量同步）"""
        existing = await self.provider_repo.find_by_id(db, provider_id)
        if not existing:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")

        if data.is_default == 1:
            await self.provider_repo.clear_default(db)

        update_data = data.model_dump(exclude_unset=True, exclude={"models"})
        if update_data:
            await self.provider_repo.update(db, provider_id, update_data)

        # 模型同步
        if data.models is not None:
            await self.model_repo.sync_models(
                db, provider_id, [m.model_dump() for m in data.models]
            )

        return await self.get_provider(db, provider_id)

    async def toggle_provider_enabled(self, db: AsyncSession, provider_id: int) -> ProviderOut:
        """切换启用/禁用状态"""
        existing = await self.provider_repo.find_by_id(db, provider_id)
        if not existing:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")
        new_enabled = 0 if existing.is_enabled == 1 else 1
        await self.provider_repo.update(db, provider_id, {"is_enabled": new_enabled})
        return await self.get_provider(db, provider_id)

    async def delete_provider(self, db: AsyncSession, provider_id: int) -> bool:
        """删除供应商（联动软删除模型）"""
        result = await self.provider_repo.soft_delete(db, provider_id)
        if not result:
            raise RecordNotFoundError(f"供应商 {provider_id} 不存在")
        await self.model_repo.delete_by_provider(db, provider_id)
        return True

    # ── 模型 CRUD ───────────────────────────────────────────

    async def list_models(self, db: AsyncSession, provider_id: int) -> List[LLMModelOut]:
        """获取供应商下所有模型"""
        models = await self.model_repo.find_by_provider(db, provider_id)
        return [LLMModelOut.model_validate(m) for m in models]

    async def create_model(self, db: AsyncSession, provider_id: int, data: LLMModelCreate) -> LLMModelOut:
        """创建单个模型"""
        model = await self.model_repo.create(db, {
            **data.model_dump(),
            "provider_id": provider_id,
        })
        return LLMModelOut.model_validate(model)

    async def update_model(self, db: AsyncSession, model_id: int, data: LLMModelUpdate) -> LLMModelOut:
        """更新单个模型"""
        existing = await self.model_repo.find_by_id(db, model_id)
        if not existing:
            raise RecordNotFoundError(f"模型 {model_id} 不存在")
        model = await self.model_repo.update(db, model_id, data.model_dump(exclude_unset=True))
        return LLMModelOut.model_validate(model)

    async def delete_model(self, db: AsyncSession, model_id: int) -> bool:
        """删除单个模型"""
        result = await self.model_repo.soft_delete(db, model_id)
        if not result:
            raise RecordNotFoundError(f"模型 {model_id} 不存在")
        return True

    async def toggle_model_enabled(self, db: AsyncSession, model_id: int) -> LLMModelOut:
        """切换模型启用状态"""
        existing = await self.model_repo.find_by_id(db, model_id)
        if not existing:
            raise RecordNotFoundError(f"模型 {model_id} 不存在")
        new_enabled = 0 if existing.is_enabled == 1 else 1
        model = await self.model_repo.update(db, model_id, {"is_enabled": new_enabled})
        return LLMModelOut.model_validate(model)

    # ── 内部方法 ─────────────────────────────────────────────

    @staticmethod
    def _to_provider_out(provider, models=None) -> ProviderOut:
        """ORM → Pydantic（含模型列表）"""
        return ProviderOut(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            base_url=provider.base_url,
            api_key=provider.api_key or "",
            is_enabled=provider.is_enabled,
            is_default=provider.is_default,
            description=provider.description or "",
            models=[LLMModelOut.model_validate(m) for m in (models or [])],
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )
