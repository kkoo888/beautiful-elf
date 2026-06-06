"""用户 Repository"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.user import User


class UserRepository:
    def __init__(self):
        self.mapper = MySQLMapper(User)

    async def find_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        return await self.mapper.find_by_id(db, user_id)

    async def find_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username, User.is_deleted == 0)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> User:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, user_id: int, data: dict) -> Optional[User]:
        return await self.mapper.update(db, user_id, data)
