"""大模型供应商 API — RESTful 规范"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.llm_provider_service import LLMProviderService
from app.schemas.llm_provider import ProviderCreate, ProviderUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = LLMProviderService()


@router.get("")
async def list_providers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """供应商列表"""
    items, total = await _service.list(db, page=page, page_size=page_size)
    return ok_page(items, total, page, page_size)


@router.get("/enabled")
async def list_enabled_providers(db: AsyncSession = Depends(get_db)):
    """获取所有启用的供应商（用于模型选择下拉）"""
    items = await _service.list_enabled(db)
    return ok(items)


@router.get("/{provider_id}")
async def get_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个供应商"""
    return ok(await _service.get(db, provider_id))


@router.post("")
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)):
    """创建供应商"""
    return ok(await _service.create(db, data))


@router.put("/{provider_id}")
async def update_provider(provider_id: int, data: ProviderUpdate, db: AsyncSession = Depends(get_db)):
    """更新供应商"""
    return ok(await _service.update(db, provider_id, data))


@router.put("/{provider_id}/toggle")
async def toggle_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    """切换供应商启用/禁用状态"""
    return ok(await _service.toggle_enabled(db, provider_id))


@router.delete("/{provider_id}")
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    """删除供应商"""
    await _service.delete(db, provider_id)
    return ok(message="删除成功")
