"""会话管理 API — RESTful 规范"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.conversation_service import ConversationService
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationOut
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = ConversationService()


@router.get("", response_model=ApiPageResult[ConversationOut])
async def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ConversationOut]:
    items, total = await _service.list(db, page, page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.get("/{conversation_id}", response_model=ApiResult[ConversationOut])
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ConversationOut]:
    item = await _service.get_by_id(db, conversation_id)
    return ApiResult(data=item)


@router.post("", response_model=ApiResult[ConversationOut])
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ConversationOut]:
    item = await _service.create(db, data)
    return ApiResult(data=item)


@router.put("/{conversation_id}", response_model=ApiResult[ConversationOut])
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ConversationOut]:
    item = await _service.update(db, conversation_id, data)
    return ApiResult(data=item)


@router.delete("/{conversation_id}", response_model=ApiResult)
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    await _service.delete(db, conversation_id)
    return ApiResult(message="删除成功")
