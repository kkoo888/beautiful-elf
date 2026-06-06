"""命令使用统计 API — RESTful 规范"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.command_usage_service import CommandUsageService
from app.schemas.command_usage import CommandUsageOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = CommandUsageService()


@router.post("/record", response_model=ApiResult[CommandUsageOut])
async def record_use(
    command_id: int = Query(..., description="命令 ID", alias="commandId"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[CommandUsageOut]:
    item = await _service.record_command_use(db, command_id)
    return ApiResult(data=item)


@router.get("/top", response_model=ApiResult[List[CommandUsageOut]])
async def top_commands(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[List[CommandUsageOut]]:
    items = await _service.get_top_commands(db, limit)
    return ApiResult(data=items)


@router.get("", response_model=ApiPageResult[CommandUsageOut])
async def list_command_usage(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[CommandUsageOut]:
    items, total = await _service.list_command_usages(db, page, page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)
