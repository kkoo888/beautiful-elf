"""会话管理 API — RESTful 规范"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.conversation_service import ConversationService
from app.schemas.conversation import ConversationCreate, ConversationUpdate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = ConversationService()


@router.get("")
async def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size)
    return ok_page(items, total, page, page_size)


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, conversation_id))


@router.post("")
async def create_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.put("/{conversation_id}")
async def update_conversation(conversation_id: int, data: ConversationUpdate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.update(db, conversation_id, data))


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, conversation_id)
    return ok(message="删除成功")
