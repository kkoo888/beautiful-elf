"""命令面板 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.command_service import CommandService
from app.schemas.command import CommandCreate, CommandUpdate, CommandOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = CommandService()


@router.get("", response_model=ApiPageResult[CommandOut])
async def list_commands(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    module: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[CommandOut]:
    items, total = await _service.list(db, page, page_size, module)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/{command_id}", response_model=ApiResult[CommandOut])
async def get_command(
    command_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[CommandOut]:
    item = await _service.get_by_id(db, command_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[CommandOut])
async def create_command(
    data: CommandCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[CommandOut]:
    item = await _service.create(db, data)
    return ApiResult(data=item)


@router.put("/{command_id}", response_model=ApiResult[CommandOut])
async def update_command(
    command_id: int,
    data: CommandUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[CommandOut]:
    item = await _service.update(db, command_id, data)
    return ApiResult(data=item)


@router.delete("/{command_id}", response_model=ApiResult)
async def delete_command(
    command_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    await _service.delete(db, command_id)
    return ApiResult(message="删除成功")


@router.post("/{command_id}/use", response_model=ApiResult)
async def record_use(
    command_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    return ApiResult(data=await _service.record_usage(db, command_id))
