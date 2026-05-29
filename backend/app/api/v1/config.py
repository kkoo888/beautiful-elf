"""配置管理 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.config_service import ConfigService
from app.schemas.config import SettingCreate, SettingUpdate
from app.schemas.response import success, page_success

router = APIRouter()
_service = ConfigService()


@router.get("")
async def list_config(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page=page, page_size=page_size)
    return page_success(items, total, page, page_size)


@router.get("/{key}")
async def get_config(key: str, db: AsyncSession = Depends(get_db)):
    return success(await _service.get_by_key(db, key))


@router.post("")
async def create_config(data: SettingCreate, db: AsyncSession = Depends(get_db)):
    return success(await _service.create(db, data))


@router.put("/{key}")
async def update_config(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    return success(await _service.update(db, key, data))


@router.delete("/{key}")
async def delete_config(key: str, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, key)
    return success(message="删除成功")
