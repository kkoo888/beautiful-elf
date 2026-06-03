"""剪贴板 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.clipboard_service import ClipboardService
from app.schemas.clipboard import ClipboardItemCreate, ClipboardItemUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = ClipboardService()


@router.get("")
async def list_clipboard_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    content_type: Optional[int] = Query(default=None),, alias="contentType")
    pinned: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, content_type, pinned)
    return ok_page(items, total, page, page_size)


@router.get("/{item_id}")
async def get_clipboard_item(item_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, item_id))


@router.post("")
async def create_clipboard_item(data: ClipboardItemCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.put("/{item_id}")
async def update_clipboard_item(item_id: int, data: ClipboardItemUpdate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.update(db, item_id, data))


@router.delete("/{item_id}")
async def delete_clipboard_item(item_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, item_id)
    return ok(message="删除成功")


@router.put("/{item_id}/pin")
async def toggle_pin(item_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.toggle_pin(db, item_id))
