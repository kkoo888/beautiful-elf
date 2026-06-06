"""消息记录 Repository"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import Message


class MessageRepository:
    def __init__(self):
        self.mapper = MySQLMapper(Message)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Message]:
        return await self.mapper.find_by_id(db, id)

    async def find_by_conversation(
        self, db: AsyncSession, conversation_id: int, offset: int = 0, limit: int = 50,
    ) -> List[Message]:
        """按会话分页查询消息"""
        return await self.mapper.find_all(
            db,
            filters={"conversation_id": conversation_id},
            offset=offset,
            limit=limit,
            order_by=Message.created_at.asc(),
        )

    async def create(self, db: AsyncSession, data: dict) -> Message:
        return await self.mapper.create(db, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def count_by_conversation(self, db: AsyncSession, conversation_id: int) -> int:
        return await self.mapper.count(db, filters={"conversation_id": conversation_id})
