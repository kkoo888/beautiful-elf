"""会话管理 Repository"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import Conversation


class ConversationRepository:
    def __init__(self):
        self.mapper = MySQLMapper(Conversation)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Conversation]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
    ) -> List[Conversation]:
        return await self.mapper.find_all(
            db, offset=offset, limit=limit, order_by=Conversation.last_message_at.desc()
        )

    async def count(self, db: AsyncSession) -> int:
        return await self.mapper.count(db)

    async def create(self, db: AsyncSession, data: dict) -> Conversation:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[Conversation]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def increment_message_count(self, db: AsyncSession, id: int) -> None:
        """消息计数 +1，更新最后消息时间"""
        conv = await self.find_by_id(db, id)
        if conv:
            await self.mapper.update(db, id, {
                "message_count": conv.message_count + 1,
                "last_message_at": datetime.now(),
            })
