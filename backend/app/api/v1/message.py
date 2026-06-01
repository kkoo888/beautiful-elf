"""消息记录 API — 嵌套在 /conversations/{id}/messages 下"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.message_service import MessageService
from app.schemas.message import MessageCreate
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = MessageService()


@router.get("")
async def list_messages(
    conversation_id: int = Path(..., description="会话 ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """消息列表 — 按会话过滤"""
    items, total = await _service.list_by_conversation(db, conversation_id, page, page_size)
    return ok_page(items, total, page, page_size)


@router.get("/{message_id}")
async def get_message(
    conversation_id: int = Path(..., description="会话 ID"),
    message_id: int = Path(..., description="消息 ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取单条消息"""
    return ok(await _service.get_by_id(db, message_id))


@router.post("")
async def create_message(
    conversation_id: int = Path(..., description="会话 ID"),
    data: MessageCreate = ...,
    db: AsyncSession = Depends(get_db),
):
    """创建消息 — conversation_id 从路径取，body 中无需传"""
    # 路径中的 conversation_id 覆盖 body 中的
    data.conversation_id = conversation_id
    return ok(await _service.create(db, data))


@router.delete("/{message_id}")
async def delete_message(
    conversation_id: int = Path(..., description="会话 ID"),
    message_id: int = Path(..., description="消息 ID"),
    db: AsyncSession = Depends(get_db),
):
    """删除消息"""
    await _service.delete(db, message_id)
    return ok(message="删除成功")
