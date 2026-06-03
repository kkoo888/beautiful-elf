"""备份管理 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.backup_service import BackupService
from app.schemas.backup import BackupCreate, BackupStatusUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = BackupService()


@router.post("")
async def create_backup(data: BackupCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.get("/{backup_id}")
async def get_backup(backup_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, backup_id))


@router.get("")
async def list_backups(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    backup_type: Optional[int] = Query(default=None, alias="backupType"),
    status: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, backup_type, status)
    return ok_page(items, total, page, page_size)


@router.patch("/{backup_id}/status")
async def update_backup_status(
    backup_id: int, data: BackupStatusUpdate, db: AsyncSession = Depends(get_db)
):
    return ok(await _service.update_status(db, backup_id, data))
