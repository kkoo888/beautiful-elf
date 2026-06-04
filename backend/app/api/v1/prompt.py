"""Prompt 版本管理 API — RESTful 规范"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.prompt_service import PromptService
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = PromptService()


@router.post("", response_model=ApiResult[PromptOut])
async def create_prompt(data: PromptCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[PromptOut]:
    item = await _service.create(db, data)
    return ApiResult(data=item)


@router.get("/active", response_model=ApiResult[PromptOut])
async def get_active_prompt(
    name: str = Query(..., description="Prompt 名称"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[PromptOut]:
    item = await _service.get_active(db, name)
    return ApiResult(data=item)


@router.get("/versions", response_model=ApiResult[List[PromptOut]])
async def get_prompt_versions(
    name: str = Query(..., description="Prompt 名称"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[List[PromptOut]]:
    items = await _service.get_versions(db, name)
    return ApiResult(data=items)


@router.get("/{prompt_id}", response_model=ApiResult[PromptOut])
async def get_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[PromptOut]:
    item = await _service.get_by_id(db, prompt_id)
    return ApiResult(data=item)


@router.get("", response_model=ApiPageResult[PromptOut])
async def list_prompts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    name: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[PromptOut]:
    items, total = await _service.list(db, page, page_size, name)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.put("/{prompt_id}", response_model=ApiResult[PromptOut])
async def update_prompt(prompt_id: int, data: PromptUpdate, db: AsyncSession = Depends(get_db)) -> ApiResult[PromptOut]:
    item = await _service.update(db, prompt_id, data)
    return ApiResult(data=item)


@router.delete("/{prompt_id}", response_model=ApiResult)
async def delete_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete(db, prompt_id)
    return ApiResult(message="删除成功")


@router.patch("/{prompt_id}/activate", response_model=ApiResult[PromptOut])
async def activate_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[PromptOut]:
    item = await _service.activate(db, prompt_id)
    return ApiResult(data=item)
