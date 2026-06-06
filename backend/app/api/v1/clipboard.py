"""剪贴板 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.clipboard_service import ClipboardService
from app.schemas.clipboard import ClipboardItemCreate, ClipboardItemUpdate, ClipboardItemOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = ClipboardService()


@router.get("", response_model=ApiPageResult[ClipboardItemOut])
async def list_clipboard_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    content_type: Optional[int] = Query(default=None, alias="contentType"),
    pinned: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ClipboardItemOut]:
    items, total = await _service.list_clipboard_items(db, page, page_size, content_type, pinned)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/{item_id}", response_model=ApiResult[ClipboardItemOut])
async def get_clipboard_item(item_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ClipboardItemOut]:
    item = await _service.get_clipboard_item_by_id(db, item_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[ClipboardItemOut])
async def create_clipboard_item(data: ClipboardItemCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[ClipboardItemOut]:
    item = await _service.create_clipboard_item(db, data)
    return ApiResult(data=item)


@router.put("/{item_id}", response_model=ApiResult[ClipboardItemOut])
async def update_clipboard_item(item_id: int, data: ClipboardItemUpdate, db: AsyncSession = Depends(get_db)) -> ApiResult[ClipboardItemOut]:
    item = await _service.update_clipboard_item(db, item_id, data)
    return ApiResult(data=item)


@router.delete("/{item_id}", response_model=ApiResult)
async def delete_clipboard_item(item_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete_clipboard_item(db, item_id)
    return ApiResult(message="删除成功")


@router.put("/{item_id}/pin", response_model=ApiResult[ClipboardItemOut])
async def toggle_pin(item_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ClipboardItemOut]:
    item = await _service.toggle_clipboard_pin(db, item_id)
    return ApiResult(data=item)
