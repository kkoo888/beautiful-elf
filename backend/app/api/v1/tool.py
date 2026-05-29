"""工具管理 API"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.tool_service import ToolService
from app.schemas.tool import ToolCreate, ToolUpdate
from app.schemas.response import success as ok_response, page_success

router = APIRouter()
_service = ToolService()


@router.post("")
async def create_tool(data: ToolCreate, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.create(db, data))


@router.get("/{tool_id}")
async def get_tool(tool_id: int, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.get_by_id(db, tool_id))


@router.get("")
async def list_tools(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    enabled: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, enabled=enabled)
    return page_success(items, total, page, page_size)


@router.put("/{tool_id}")
async def update_tool(tool_id: int, data: ToolUpdate, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.update(db, tool_id, data))


@router.delete("/{tool_id}")
async def delete_tool(tool_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, tool_id)
    return ok_response(message="删除成功")


@router.patch("/{tool_id}/enable")
async def enable_tool(tool_id: int, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.enable(db, tool_id))


@router.patch("/{tool_id}/disable")
async def disable_tool(tool_id: int, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.disable(db, tool_id))


@router.get("/{tool_id}/stats")
async def get_tool_stats(tool_id: int, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.get_stats(db, tool_id))


@router.post("/{tool_id}/stats/record")
async def record_tool_call(
    tool_id: int,
    success_flag: bool = Query(..., alias="success"),
    duration_ms: int = Query(..., ge=0),
    db: AsyncSession = Depends(get_db),
):
    return ok_response(await _service.record_call(db, tool_id, success_flag, duration_ms))
