"""通知系统 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationCreate, NotificationOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = NotificationService()


@router.get("", response_model=ApiPageResult[NotificationOut])
async def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    notif_type: Optional[str] = Query(default=None, alias="type"),
    read_status: Optional[int] = Query(default=None, alias="read"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[NotificationOut]:
    items, total = await _service.list_notifications(db, page, page_size, notif_type, read_status)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/{notification_id}", response_model=ApiResult[NotificationOut])
async def get_notification(notification_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[NotificationOut]:
    item = await _service.get_notification_by_id(db, notification_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[NotificationOut])
async def create_notification(data: NotificationCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[NotificationOut]:
    item = await _service.create_notification(db, data)
    return ApiResult(data=item)


@router.delete("/{notification_id}", response_model=ApiResult)
async def delete_notification(notification_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete_notification(db, notification_id)
    return ApiResult(message="删除成功")


@router.put("/{notification_id}/read", response_model=ApiResult[NotificationOut])
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[NotificationOut]:
    item = await _service.mark_notification_read(db, notification_id)
    return ApiResult(data=item)


@router.put("/read-all", response_model=ApiResult)
async def mark_all_read(db: AsyncSession = Depends(get_db)) -> ApiResult:
    count = await _service.mark_all_notifications_read(db)
    return ApiResult(data={"marked": count})
