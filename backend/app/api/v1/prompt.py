"""Prompt 版本管理 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.prompt_service import PromptService
from app.schemas.prompt import PromptCreate, PromptUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = PromptService()


@router.post("")
async def create_prompt(data: PromptCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.get("/active")
async def get_active_prompt(
    name: str = Query(..., description="Prompt 名称"),
    db: AsyncSession = Depends(get_db),
):
    return ok(await _service.get_active(db, name))


@router.get("/versions")
async def get_prompt_versions(
    name: str = Query(..., description="Prompt 名称"),
    db: AsyncSession = Depends(get_db),
):
    return ok(await _service.get_versions(db, name))


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, prompt_id))


@router.get("")
async def list_prompts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    name: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, name)
    return ok_page(items, total, page, page_size)


@router.put("/{prompt_id}")
async def update_prompt(prompt_id: int, data: PromptUpdate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.update(db, prompt_id, data))


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, prompt_id)
    return ok(message="删除成功")


@router.patch("/{prompt_id}/activate")
async def activate_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.activate(db, prompt_id))
