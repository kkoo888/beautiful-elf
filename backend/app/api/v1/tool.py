"""工具管理 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.tool_service import ToolService
from app.schemas.tool import ToolCreate, ToolUpdate, ToolOut, ToolStatsOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = ToolService()


@router.post("", response_model=ApiResult[ToolOut])
async def create_tool(data: ToolCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[ToolOut]:
    item = await _service.create(db, data)
    return ApiResult(data=item)


@router.get("/{tool_id}", response_model=ApiResult[ToolOut])
async def get_tool(tool_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ToolOut]:
    item = await _service.get_by_id(db, tool_id)
    return ApiResult(data=item)


@router.get("", response_model=ApiPageResult[ToolOut])
async def list_tools(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    enabled: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ToolOut]:
    items, total = await _service.list(db, page, page_size, enabled=enabled)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.put("/{tool_id}", response_model=ApiResult[ToolOut])
async def update_tool(tool_id: int, data: ToolUpdate, db: AsyncSession = Depends(get_db)) -> ApiResult[ToolOut]:
    item = await _service.update(db, tool_id, data)
    return ApiResult(data=item)


@router.delete("/{tool_id}", response_model=ApiResult)
async def delete_tool(tool_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete(db, tool_id)
    return ApiResult(message="删除成功")


@router.patch("/{tool_id}/enable", response_model=ApiResult[ToolOut])
async def enable_tool(tool_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ToolOut]:
    item = await _service.enable(db, tool_id)
    return ApiResult(data=item)


@router.patch("/{tool_id}/disable", response_model=ApiResult[ToolOut])
async def disable_tool(tool_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ToolOut]:
    item = await _service.disable(db, tool_id)
    return ApiResult(data=item)


@router.get("/{tool_id}/stats", response_model=ApiResult[ToolStatsOut])
async def get_tool_stats(tool_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[ToolStatsOut]:
    item = await _service.get_stats(db, tool_id)
    return ApiResult(data=item)


@router.post("/{tool_id}/stats/record", response_model=ApiResult[ToolStatsOut])
async def record_tool_call(
    tool_id: int,
    success_flag: bool = Query(..., alias="success"),
    duration_ms: int = Query(..., ge=0, alias="durationMs"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ToolStatsOut]:
    item = await _service.record_call(db, tool_id, success_flag, duration_ms)
    return ApiResult(data=item)
