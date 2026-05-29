"""日程管理 API — RESTful 规范"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.schedule_service import ScheduleService
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = ScheduleService()


@router.get("")
async def list_schedules(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, start_time, end_time)
    return ok_page(items, total, page, page_size)


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, schedule_id))


@router.post("")
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: int, data: ScheduleUpdate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.update(db, schedule_id, data))


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, schedule_id)
    return ok(message="删除成功")
