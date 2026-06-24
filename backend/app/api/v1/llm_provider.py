"""大模型供应商 + 模型 + Tier配置 API — RESTful 规范"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.llm_provider_service import LLMProviderService
from app.services.tier_config_service import TierConfigService
from app.schemas.llm_provider import (
    ProviderCreate, ProviderUpdate, ProviderOut,
    LLMModelCreate, LLMModelUpdate, LLMModelOut,
    TierConfigCreate, TierConfigUpdate, TierConfigOut,
)
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = LLMProviderService()
_tier_service = TierConfigService()


# ── 供应商端点 ─────────────────────────────────────────────

@router.get("", response_model=ApiPageResult[ProviderOut])
async def list_providers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ProviderOut]:
    """供应商列表（分页，含模型列表）"""
    items, total = await _service.list_providers(db, page=page, page_size=page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/enabled", response_model=ApiResult[List[ProviderOut]])
async def list_enabled_providers(db: AsyncSession = Depends(get_db)) -> ApiResult[List[ProviderOut]]:
    """获取所有启用的供应商（含启用模型，用于前端模型选择）"""
    items = await _service.list_enabled_providers(db)
    return ApiResult(data=items)


@router.get("/{provider_id}", response_model=ApiResult[ProviderOut])
async def get_provider(provider_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ProviderOut]:
    """获取单个供应商（含模型）"""
    item = await _service.get_provider(db, provider_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[ProviderOut])
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[ProviderOut]:
    """创建供应商（可附带模型列表）"""
    item = await _service.create_provider(db, data)
    return ApiResult(data=item)


@router.put("/{provider_id}", response_model=ApiResult[ProviderOut])
async def update_provider(provider_id: int, data: ProviderUpdate, db: AsyncSession = Depends(get_db)) -> ApiResult[ProviderOut]:
    """更新供应商（models 传入则全量同步模型列表）"""
    item = await _service.update_provider(db, provider_id, data)
    return ApiResult(data=item)


@router.put("/{provider_id}/toggle", response_model=ApiResult[ProviderOut])
async def toggle_provider(provider_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ProviderOut]:
    """切换供应商启用/禁用状态"""
    item = await _service.toggle_provider_enabled(db, provider_id)
    return ApiResult(data=item)


@router.delete("/{provider_id}", response_model=ApiResult)
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    """删除供应商（联动删除模型）"""
    await _service.delete_provider(db, provider_id)
    return ApiResult(message="删除成功")


# ── 模型端点 ───────────────────────────────────────────────

@router.get("/{provider_id}/models", response_model=ApiResult[List[LLMModelOut]])
async def list_models(provider_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[List[LLMModelOut]]:
    """获取供应商下所有模型"""
    items = await _service.list_models(db, provider_id)
    return ApiResult(data=items)


@router.post("/{provider_id}/models", response_model=ApiResult[LLMModelOut])
async def create_model(
    provider_id: int, data: LLMModelCreate, db: AsyncSession = Depends(get_db)
) -> ApiResult[LLMModelOut]:
    """为供应商添加单个模型"""
    item = await _service.create_model(db, provider_id, data)
    return ApiResult(data=item)


@router.put("/{provider_id}/models/{model_id}", response_model=ApiResult[LLMModelOut])
async def update_model(
    provider_id: int, model_id: int, data: LLMModelUpdate, db: AsyncSession = Depends(get_db)
) -> ApiResult[LLMModelOut]:
    """更新单个模型"""
    item = await _service.update_model(db, model_id, data)
    return ApiResult(data=item)


@router.put("/{provider_id}/models/{model_id}/toggle", response_model=ApiResult[LLMModelOut])
async def toggle_model(provider_id: int, model_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[LLMModelOut]:
    """切换模型启用/禁用状态"""
    item = await _service.toggle_model_enabled(db, model_id)
    return ApiResult(data=item)


@router.delete("/{provider_id}/models/{model_id}", response_model=ApiResult)
async def delete_model(provider_id: int, model_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    """删除单个模型"""
    await _service.delete_model(db, model_id)
    return ApiResult(message="删除成功")


# ── Tier 配置端点 ─────────────────────────────────────────

@router.get("/tier-mapping", response_model=ApiResult[List[TierConfigOut]])
async def list_tier_configs(db: AsyncSession = Depends(get_db)) -> ApiResult[List[TierConfigOut]]:
    """查询所有启用的 tier 配置"""
    items = await _tier_service.list_all(db)
    return ApiResult(data=items)


@router.get("/{provider_id}/tier-mapping", response_model=ApiResult[List[TierConfigOut]])
async def list_provider_tier_configs(provider_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[List[TierConfigOut]]:
    """查询某个供应商的 tier 配置"""
    items = await _tier_service.list_by_provider(db, provider_id)
    return ApiResult(data=items)


@router.post("/{provider_id}/tier-mapping", response_model=ApiResult[TierConfigOut])
async def upsert_tier_config(
    provider_id: int, data: TierConfigCreate, db: AsyncSession = Depends(get_db)
) -> ApiResult[TierConfigOut]:
    """创建或更新 tier 配置"""
    data.provider_id = provider_id
    item = await _tier_service.upsert(db, data)
    return ApiResult(data=item)


@router.put("/tier-mapping/{config_id}", response_model=ApiResult[TierConfigOut])
async def update_tier_config(
    config_id: int, data: TierConfigUpdate, db: AsyncSession = Depends(get_db)
) -> ApiResult[TierConfigOut]:
    """更新 tier 配置"""
    item = await _tier_service.update(db, config_id, data)
    return ApiResult(data=item)


@router.delete("/tier-mapping/{tier}", response_model=ApiResult)
async def delete_tier_configs(tier: str, db: AsyncSession = Depends(get_db)) -> ApiResult:
    """删除某个 tier 的所有配置"""
    count = await _tier_service.delete_by_tier(db, tier)
    return ApiResult(message=f"删除 {count} 条配置")
