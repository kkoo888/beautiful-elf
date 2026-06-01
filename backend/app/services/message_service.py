"""消息记录 Service"""
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.message_repo import MessageRepository
from app.repository.conversation_repo import ConversationRepository
from app.schemas.message import MessageCreate
from app.core.exceptions import RecordNotFoundError


class MessageService:
    def __init__(self):
        self.repo = MessageRepository()
        self.conv_repo = ConversationRepository()

    async def create(self, db: AsyncSession, data: MessageCreate) -> dict:
        # 校验会话存在
        conv = await self.conv_repo.find_by_id(db, data.conversation_id)
        if not conv:
            raise RecordNotFoundError("会话不存在")
        msg = await self.repo.create(db, data.model_dump())
        # 更新会话计数
        await self.conv_repo.increment_message_count(db, data.conversation_id)
        return self._to_dict(msg)

    async def get_by_id(self, db: AsyncSession, msg_id: int) -> dict:
        msg = await self.repo.find_by_id(db, msg_id)
        if not msg:
            raise RecordNotFoundError("消息不存在")
        return self._to_dict(msg)

    async def list_by_conversation(
        self, db: AsyncSession, conversation_id: int, page: int = 1, page_size: int = 50,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_by_conversation(db, conversation_id, offset=offset, limit=page_size)
        total = await self.repo.count_by_conversation(db, conversation_id)
        return [self._to_dict(m) for m in items], total

    async def delete(self, db: AsyncSession, msg_id: int) -> bool:
        msg = await self.repo.find_by_id(db, msg_id)
        if not msg:
            raise RecordNotFoundError("消息不存在")
        return await self.repo.soft_delete(db, msg_id)

    @staticmethod
    def _to_dict(msg) -> dict:
        return {
            "id": msg.id,
            "conversationId": msg.conversation_id,
            "role": msg.role,
            "content": msg.content,
            "toolCalls": msg.tool_calls,
            "toolCallId": msg.tool_call_id,
            "tokenCount": msg.token_count,
            "createdAt": str(msg.created_at) if msg.created_at else None,
            "updatedAt": str(msg.updated_at) if msg.updated_at else None,
        }
