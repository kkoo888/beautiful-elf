"""会话管理 Service"""
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.conversation_repo import ConversationRepository
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationOut
from app.core.exceptions import RecordNotFoundError


class ConversationService:
    def __init__(self):
        self.repo = ConversationRepository()

    async def create_conversation(self, db: AsyncSession, data: ConversationCreate) -> ConversationOut:
        conv = await self.repo.create(db, data.model_dump())
        return self._to_out(conv)

    async def get_conversation_by_id(self, db: AsyncSession, conv_id: int) -> ConversationOut:
        conv = await self.repo.find_by_id(db, conv_id)
        if not conv:
            raise RecordNotFoundError("会话不存在")
        return self._to_out(conv)

    async def list_conversations(self, db: AsyncSession, page: int = 1, page_size: int = 20) -> Tuple[List[ConversationOut], int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size)
        total = await self.repo.count(db)
        return [self._to_out(c) for c in items], total

    async def update_conversation(self, db: AsyncSession, conv_id: int, data: ConversationUpdate) -> ConversationOut:
        existing = await self.repo.find_by_id(db, conv_id)
        if not existing:
            raise RecordNotFoundError("会话不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_out(existing)
        conv = await self.repo.update(db, conv_id, update_data)
        return self._to_out(conv)

    async def delete_conversation(self, db: AsyncSession, conv_id: int) -> bool:
        existing = await self.repo.find_by_id(db, conv_id)
        if not existing:
            raise RecordNotFoundError("会话不存在")
        return await self.repo.soft_delete(db, conv_id)

    @staticmethod
    def _to_out(conv) -> ConversationOut:
        """ORM → Pydantic 模型"""
        return ConversationOut.model_validate(conv)
