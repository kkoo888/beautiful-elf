"""消息记录 API — 扁平路由 + query 过滤"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.message_service import MessageService
from app.schemas.message import MessageCreate, MessageOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = MessageService()


@router.get("", response_model=ApiPageResult[MessageOut])
async def list_messages(
    conversation_id: int = Query(..., description="会话 ID（必填，用于过滤）", alias="conversationId"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[MessageOut]:
    """消息列表 — 按会话过滤"""
    items, total = await _service.list_by_conversation(db, conversation_id, page, page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/{message_id}", response_model=ApiResult[MessageOut])
async def get_message(message_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[MessageOut]:
    """获取单条消息"""
    item = await _service.get_message_by_id(db, message_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[MessageOut])
async def create_message(data: MessageCreate, db: AsyncSession = Depends(get_db)) -> ApiResult[MessageOut]:
    """创建消息 — conversation_id 在 body 中必填"""
    item = await _service.create_message(db, data)
    return ApiResult(data=item)


@router.delete("/{message_id}", response_model=ApiResult)
async def delete_message(message_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    """删除消息"""
    await _service.delete_message(db, message_id)
    return ApiResult(message="删除成功")
