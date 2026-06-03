"""AI 回答反馈 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ai_feedback_service import AIFeedbackService
from app.schemas.ai_feedback import AIFeedbackCreate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = AIFeedbackService()


@router.post("")
async def create_feedback(data: AIFeedbackCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.get("/stats")
async def get_feedback_stats(db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_stats(db))


@router.get("/{feedback_id}")
async def get_feedback(feedback_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, feedback_id))


@router.get("")
async def list_feedbacks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    feedback_type: Optional[int] = Query(default=None, alias="feedbackType"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, feedback_type)
    return ok_page(items, total, page, page_size)
