"""代码片段 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.snippet_service import SnippetService
from app.schemas.snippet import SnippetCreate, SnippetUpdate, SnippetOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = SnippetService()


@router.get("", response_model=ApiPageResult[SnippetOut])
async def list_snippets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    language: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[SnippetOut]:
    items, total = await _service.list_snippets(db, page, page_size, language, tag)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/{snippet_id}", response_model=ApiResult[SnippetOut])
async def get_snippet(snippet_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[SnippetOut]:
    item = await _service.get_snippet_by_id(db, snippet_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[SnippetOut])
async def create_snippet(data: SnippetCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[SnippetOut]:
    item = await _service.create_snippet(db, data)
    return ApiResult(data=item)


@router.put("/{snippet_id}", response_model=ApiResult[SnippetOut])
async def update_snippet(snippet_id: int, data: SnippetUpdate, db: AsyncSession = Depends(get_db)) -> ApiResult[SnippetOut]:
    item = await _service.update_snippet(db, snippet_id, data)
    return ApiResult(data=item)


@router.delete("/{snippet_id}", response_model=ApiResult)
async def delete_snippet(snippet_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete_snippet(db, snippet_id)
    return ApiResult(message="删除成功")


@router.post("/{snippet_id}/use", response_model=ApiResult[SnippetOut])
async def record_use(snippet_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[SnippetOut]:
    item = await _service.increment_snippet_use(db, snippet_id)
    return ApiResult(data=item)
