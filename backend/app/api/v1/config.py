"""配置管理 API — RESTful 规范"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.config_service import ConfigService
from app.schemas.config import SettingCreate, SettingUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = ConfigService()


@router.get("")
async def list_configs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """配置列表"""
    items, total = await _service.list(db, page=page, page_size=page_size)
    return ok_page(items, total, page, page_size)


@router.get("/{key}")
async def get_config(key: str, db: AsyncSession = Depends(get_db)):
    """获取单个配置"""
    return ok(await _service.get_by_key(db, key))


@router.post("")
async def create_config(data: SettingCreate, db: AsyncSession = Depends(get_db)):
    """创建配置"""
    return ok(await _service.create(db, data))


@router.put("/{key}")
async def update_config(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """更新配置"""
    return ok(await _service.update(db, key, data))


@router.delete("/{key}")
async def delete_config(key: str, db: AsyncSession = Depends(get_db)):
    """删除配置"""
    await _service.delete(db, key)
    return ok(message="删除成功")
