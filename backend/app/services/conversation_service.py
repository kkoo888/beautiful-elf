"""会话管理 Service"""
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.conversation_repo import ConversationRepository
from app.schemas.conversation import ConversationCreate, ConversationUpdate
from app.core.exceptions import RecordNotFoundError


class ConversationService:
    def __init__(self):
        self.repo = ConversationRepository()

    async def create(self, db: AsyncSession, data: ConversationCreate) -> dict:
        conv = await self.repo.create(db, data.model_dump())
        return self._to_dict(conv)

    async def get_by_id(self, db: AsyncSession, conv_id: int) -> dict:
        conv = await self.repo.find_by_id(db, conv_id)
        if not conv:
            raise RecordNotFoundError("会话不存在")
        return self._to_dict(conv)

    async def list(self, db: AsyncSession, page: int = 1, page_size: int = 20) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size)
        total = await self.repo.count(db)
        return [self._to_dict(c) for c in items], total

    async def update(self, db: AsyncSession, conv_id: int, data: ConversationUpdate) -> dict:
        existing = await self.repo.find_by_id(db, conv_id)
        if not existing:
            raise RecordNotFoundError("会话不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_dict(existing)
        conv = await self.repo.update(db, conv_id, update_data)
        return self._to_dict(conv)

    async def delete(self, db: AsyncSession, conv_id: int) -> bool:
        existing = await self.repo.find_by_id(db, conv_id)
        if not existing:
            raise RecordNotFoundError("会话不存在")
        return await self.repo.soft_delete(db, conv_id)

    @staticmethod
    def _to_dict(conv) -> dict:
        return {
            "id": conv.id,
            "title": conv.title,
            "modelName": conv.model_name,
            "messageCount": conv.message_count,
            "lastMessageAt": str(conv.last_message_at) if conv.last_message_at else None,
            "createdAt": str(conv.created_at) if conv.created_at else None,
            "updatedAt": str(conv.updated_at) if conv.updated_at else None,
        }
