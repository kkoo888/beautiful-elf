"""备份管理 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.backup_service import BackupService
from app.schemas.backup import BackupCreate, BackupStatusUpdate, BackupOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = BackupService()


@router.post("", response_model=ApiResult[BackupOut])
async def create_backup(
    data: BackupCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[BackupOut]:
    item = await _service.create(db, data)
    return ApiResult(data=item)


@router.get("/{backup_id}", response_model=ApiResult[BackupOut])
async def get_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[BackupOut]:
    item = await _service.get_by_id(db, backup_id)
    return ApiResult(data=item)


@router.get("", response_model=ApiPageResult[BackupOut])
async def list_backups(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    backup_type: Optional[int] = Query(default=None, alias="backupType"),
    status: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[BackupOut]:
    items, total = await _service.list(db, page, page_size, backup_type, status)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.patch("/{backup_id}/status", response_model=ApiResult[BackupOut])
async def update_backup_status(
    backup_id: int,
    data: BackupStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[BackupOut]:
    item = await _service.update_status(db, backup_id, data)
    return ApiResult(data=item)
