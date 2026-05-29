"""消息记录 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.message_service import MessageService
from app.schemas.message import MessageCreate
from app.schemas.response import success, page_success

router = APIRouter()
_service = MessageService()


@router.get("")
async def list_messages(
    conversation_id: int = Query(..., description="会话 ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list_by_conversation(db, conversation_id, page, page_size)
    return page_success(items, total, page, page_size)


@router.get("/{message_id}")
async def get_message(message_id: int, db: AsyncSession = Depends(get_db)):
    return success(await _service.get_by_id(db, message_id))


@router.post("")
async def create_message(data: MessageCreate, db: AsyncSession = Depends(get_db)):
    return success(await _service.create(db, data))


@router.delete("/{message_id}")
async def delete_message(message_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, message_id)
    return success(message="删除成功")
