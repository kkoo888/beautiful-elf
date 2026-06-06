"""大模型供应商 API — RESTful 规范"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.llm_provider_service import LLMProviderService
from app.schemas.llm_provider import ProviderCreate, ProviderUpdate, ProviderOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = LLMProviderService()


@router.get("", response_model=ApiPageResult[ProviderOut])
async def list_providers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ProviderOut]:
    """供应商列表（分页）"""
    items, total = await _service.list_providers(db, page=page, page_size=page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/enabled", response_model=ApiResult[List[ProviderOut]])
async def list_enabled_providers(db: AsyncSession = Depends(get_db)) -> ApiResult[List[ProviderOut]]:
    """获取所有启用的供应商（用于模型选择下拉）"""
    items = await _service.list_enabled_providers(db)
    return ApiResult(data=items)


@router.get("/{provider_id}", response_model=ApiResult[ProviderOut])
async def get_provider(provider_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ProviderOut]:
    """获取单个供应商"""
    item = await _service.get_provider(db, provider_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[ProviderOut])
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[ProviderOut]:
    """创建供应商"""
    item = await _service.create_provider(db, data)
    return ApiResult(data=item)


@router.put("/{provider_id}", response_model=ApiResult[ProviderOut])
async def update_provider(provider_id: int, data: ProviderUpdate, db: AsyncSession = Depends(get_db)) -> ApiResult[ProviderOut]:
    """更新供应商"""
    item = await _service.update_provider(db, provider_id, data)
    return ApiResult(data=item)


@router.put("/{provider_id}/toggle", response_model=ApiResult[ProviderOut])
async def toggle_provider(provider_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ProviderOut]:
    """切换供应商启用/禁用状态"""
    item = await _service.toggle_provider_enabled(db, provider_id)
    return ApiResult(data=item)


@router.delete("/{provider_id}", response_model=ApiResult)
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    """删除供应商"""
    await _service.delete_provider(db, provider_id)
    return ApiResult(message="删除成功")
