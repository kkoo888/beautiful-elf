"""日程管理 API — RESTful 规范"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.schedule_service import ScheduleService
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = ScheduleService()


@router.get("", response_model=ApiPageResult[ScheduleOut])
async def list_schedules(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    start_time: Optional[datetime] = Query(default=None, alias="startTime"),
    end_time: Optional[datetime] = Query(default=None, alias="endTime"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ScheduleOut]:
    items, total = await _service.list(db, page, page_size, start_time, end_time)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/{schedule_id}", response_model=ApiResult[ScheduleOut])
async def get_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ScheduleOut]:
    item = await _service.get_by_id(db, schedule_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[ScheduleOut])
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[ScheduleOut]:
    item = await _service.create(db, data)
    return ApiResult(data=item)


@router.put("/{schedule_id}", response_model=ApiResult[ScheduleOut])
async def update_schedule(schedule_id: int, data: ScheduleUpdate, db: AsyncSession = Depends(get_db)) -> ApiResult[ScheduleOut]:
    item = await _service.update(db, schedule_id, data)
    return ApiResult(data=item)


@router.delete("/{schedule_id}", response_model=ApiResult)
async def delete_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete(db, schedule_id)
    return ApiResult(message="删除成功")
