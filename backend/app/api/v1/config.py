"""配置管理 API — RESTful 规范"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.config_service import ConfigService
from app.schemas.config import SettingCreate, SettingUpdate, SettingOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = ConfigService()


@router.get("", response_model=ApiPageResult[SettingOut])
async def list_configs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[SettingOut]:
    """配置列表"""
    items, total = await _service.list(db, page=page, page_size=page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/{key}", response_model=ApiResult[SettingOut])
async def get_config(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[SettingOut]:
    """获取单个配置"""
    item = await _service.get_by_key(db, key)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[SettingOut])
async def create_config(
    data: SettingCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[SettingOut]:
    """创建配置"""
    item = await _service.create(db, data)
    return ApiResult(data=item)


@router.put("/{key}", response_model=ApiResult[SettingOut])
async def update_config(
    key: str,
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[SettingOut]:
    """更新配置"""
    item = await _service.update(db, key, data)
    return ApiResult(data=item)


@router.delete("/{key}", response_model=ApiResult)
async def delete_config(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除配置"""
    await _service.delete(db, key)
    return ApiResult(message="删除成功")
