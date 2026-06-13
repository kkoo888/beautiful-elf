"""人格配置 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.soul_config_service import SoulConfigService
from app.schemas.soul_config import SoulConfigCreate, SoulConfigUpdate, SoulConfigOut
from app.schemas.response import ApiResult, ApiPageResult
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
_service = SoulConfigService()


async def _refresh_soul_cache(db: AsyncSession) -> None:
    """刷新 ContextEngine 的人格 prompt 缓存"""
    try:
        from app.services.agent_service import agent_service
        if agent_service.is_ready:
            await agent_service.refresh_soul_prompt(db)
    except Exception as e:
        logger.debug(f"人格缓存刷新跳过: {e}")


@router.get("", response_model=ApiPageResult[SoulConfigOut])
async def list_soul_configs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[SoulConfigOut]:
    items, total = await _service.list_soul_configs(db, page, page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/active", response_model=ApiResult[SoulConfigOut])
async def get_active_config(db: AsyncSession = Depends(get_db)) -> ApiResult[SoulConfigOut]:
    item = await _service.get_active_soul_config(db)
    return ApiResult(data=item)


@router.get("/{config_id}", response_model=ApiResult[SoulConfigOut])
async def get_soul_config(config_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[SoulConfigOut]:
    item = await _service.get_soul_config_by_id(db, config_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[SoulConfigOut])
async def create_soul_config(data: SoulConfigCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[SoulConfigOut]:
    item = await _service.create_soul_config(db, data)
    await _refresh_soul_cache(db)
    return ApiResult(data=item)


@router.put("/{config_id}", response_model=ApiResult[SoulConfigOut])
async def update_soul_config(config_id: int, data: SoulConfigUpdate, db: AsyncSession = Depends(get_db)) -> ApiResult[SoulConfigOut]:
    item = await _service.update_soul_config(db, config_id, data)
    await _refresh_soul_cache(db)
    return ApiResult(data=item)


@router.delete("/{config_id}", response_model=ApiResult)
async def delete_soul_config(config_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete_soul_config(db, config_id)
    await _refresh_soul_cache(db)
    return ApiResult(message="删除成功")
