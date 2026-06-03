"""通知系统 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationCreate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = NotificationService()


@router.get("")
async def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    type: Optional[str] = Query(default=None),
    read: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, type, read)
    return ok_page(items, total, page, page_size)


@router.get("/{notification_id}")
async def get_notification(notification_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, notification_id))


@router.post("")
async def create_notification(data: NotificationCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.delete("/{notification_id}")
async def delete_notification(notification_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, notification_id)
    return ok(message="删除成功")


@router.put("/{notification_id}/read")
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.mark_read(db, notification_id))


@router.put("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    count = await _service.mark_all_read(db)
    return ok({"marked": count})
