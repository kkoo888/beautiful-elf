"""命令使用统计 API — RESTful 规范"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.command_usage_service import CommandUsageService
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = CommandUsageService()


@router.post("/record")
async def record_use(
    command_id: int = Query(..., description="命令 ID", alias="commandId"),
    db: AsyncSession = Depends(get_db),
):
    return ok(await _service.record_use(db, command_id))


@router.get("/top")
async def top_commands(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return ok(await _service.top_commands(db, limit))


@router.get("")
async def list_command_usage(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size)
    return ok_page(items, total, page, page_size)
