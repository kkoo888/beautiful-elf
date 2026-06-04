"""人格配置 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.soul_config_service import SoulConfigService
from app.schemas.soul_config import SoulConfigCreate, SoulConfigUpdate, SoulConfigOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = SoulConfigService()


@router.get("", response_model=ApiPageResult[SoulConfigOut])
async def list_soul_configs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[SoulConfigOut]:
    items, total = await _service.list(db, page, page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/active", response_model=ApiResult[SoulConfigOut])
async def get_active_config(db: AsyncSession = Depends(get_db)) -> ApiResult[SoulConfigOut]:
    item = await _service.get_active(db)
    return ApiResult(data=item)


@router.get("/{config_id}", response_model=ApiResult[SoulConfigOut])
async def get_soul_config(config_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[SoulConfigOut]:
    item = await _service.get_by_id(db, config_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[SoulConfigOut])
async def create_soul_config(data: SoulConfigCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[SoulConfigOut]:
    item = await _service.create(db, data)
    return ApiResult(data=item)


@router.put("/{config_id}", response_model=ApiResult[SoulConfigOut])
async def update_soul_config(config_id: int, data: SoulConfigUpdate, db: AsyncSession = Depends(get_db)) -> ApiResult[SoulConfigOut]:
    item = await _service.update(db, config_id, data)
    return ApiResult(data=item)


@router.delete("/{config_id}", response_model=ApiResult)
async def delete_soul_config(config_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete(db, config_id)
    return ApiResult(message="删除成功")
