"""行为日志 API — RESTful 规范"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.action_log_service import ActionLogService
from app.schemas.action_log import ActionLogCreate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = ActionLogService()


@router.post("")
async def create_action_log(data: ActionLogCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.get("")
async def list_action_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    module: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    start_time: Optional[datetime] = Query(default=None, alias="startTime"),
    end_time: Optional[datetime] = Query(default=None, alias="endTime"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(
        db, page, page_size,
        module=module, action=action,
        start_time=start_time, end_time=end_time,
    )
    return ok_page(items, total, page, page_size)


@router.delete("/cleanup")
async def cleanup_old_logs(
    days: int = Query(default=7, ge=1),
    db: AsyncSession = Depends(get_db),
):
    count = await _service.cleanup_old(db, days)
    return ok({"deleted": count})
