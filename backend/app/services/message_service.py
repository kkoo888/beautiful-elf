"""消息记录 Service"""
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.message_repo import MessageRepository
from app.repository.conversation_repo import ConversationRepository
from app.schemas.message import MessageCreate, MessageOut
from app.core.exceptions import RecordNotFoundError


class MessageService:
    def __init__(self):
        self.repo = MessageRepository()
        self.conv_repo = ConversationRepository()

    @staticmethod
    def _to_out(msg) -> MessageOut:
        """ORM → Pydantic 模型"""
        return MessageOut.model_validate(msg)

    async def create(self, db: AsyncSession, data: MessageCreate) -> MessageOut:
        # 校验会话存在
        conv = await self.conv_repo.find_by_id(db, data.conversation_id)
        if not conv:
            raise RecordNotFoundError("会话不存在")
        msg = await self.repo.create(db, data.model_dump())
        # 更新会话计数
        await self.conv_repo.increment_message_count(db, data.conversation_id)
        return self._to_out(msg)

    async def get_by_id(self, db: AsyncSession, msg_id: int) -> MessageOut:
        msg = await self.repo.find_by_id(db, msg_id)
        if not msg:
            raise RecordNotFoundError("消息不存在")
        return self._to_out(msg)

    async def list_by_conversation(
        self, db: AsyncSession, conversation_id: int, page: int = 1, page_size: int = 50,
    ) -> Tuple[List[MessageOut], int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_by_conversation(db, conversation_id, offset=offset, limit=page_size)
        total = await self.repo.count_by_conversation(db, conversation_id)
        return [self._to_out(m) for m in items], total

    async def delete(self, db: AsyncSession, msg_id: int) -> bool:
        msg = await self.repo.find_by_id(db, msg_id)
        if not msg:
            raise RecordNotFoundError("消息不存在")
        return await self.repo.soft_delete(db, msg_id)
