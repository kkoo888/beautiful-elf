"""人格配置 API — RESTful 规范"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.soul_config_service import SoulConfigService
from app.schemas.soul_config import SoulConfigCreate, SoulConfigUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = SoulConfigService()


@router.get("")
async def list_soul_configs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size)
    return ok_page(items, total, page, page_size)


@router.get("/active")
async def get_active_config(db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_active(db))


@router.get("/{config_id}")
async def get_soul_config(config_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, config_id))


@router.post("")
async def create_soul_config(data: SoulConfigCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.put("/{config_id}")
async def update_soul_config(config_id: int, data: SoulConfigUpdate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.update(db, config_id, data))


@router.delete("/{config_id}")
async def delete_soul_config(config_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, config_id)
    return ok(message="删除成功")
