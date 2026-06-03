"""命令面板 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.command_service import CommandService
from app.schemas.command import CommandCreate, CommandUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = CommandService()


@router.get("")
async def list_commands(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    module: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, module)
    return ok_page(items, total, page, page_size)


@router.get("/{command_id}")
async def get_command(command_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, command_id))


@router.post("")
async def create_command(data: CommandCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.put("/{command_id}")
async def update_command(command_id: int, data: CommandUpdate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.update(db, command_id, data))


@router.delete("/{command_id}")
async def delete_command(command_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, command_id)
    return ok(message="删除成功")


@router.post("/{command_id}/use")
async def record_use(command_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.record_usage(db, command_id))
