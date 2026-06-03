"""代码片段 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.snippet_service import SnippetService
from app.schemas.snippet import SnippetCreate, SnippetUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = SnippetService()


@router.get("")
async def list_snippets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    language: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, language, tag)
    return ok_page(items, total, page, page_size)


@router.get("/{snippet_id}")
async def get_snippet(snippet_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, snippet_id))


@router.post("")
async def create_snippet(data: SnippetCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.put("/{snippet_id}")
async def update_snippet(snippet_id: int, data: SnippetUpdate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.update(db, snippet_id, data))


@router.delete("/{snippet_id}")
async def delete_snippet(snippet_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, snippet_id)
    return ok(message="删除成功")


@router.post("/{snippet_id}/use")
async def record_use(snippet_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.increment_use(db, snippet_id))
