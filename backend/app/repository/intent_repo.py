"""意图数据仓库 — MySQL intents 表 CRUD"""
from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intent import Intent
from app.core.logging import get_logger

logger = get_logger(__name__)


class IntentRepository:
    """意图数据仓库"""

    async def get_all_active(self, db: AsyncSession) -> List[Intent]:
        """获取所有启用的意图"""
        stmt = select(Intent).where(Intent.is_enabled == 1)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, intent_id: int) -> Optional[Intent]:
        """按 ID 获取意图"""
        stmt = select(Intent).where(Intent.id == intent_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> Intent:
        """创建意图"""
        intent = Intent(**data)
        db.add(intent)
        await db.flush()
        await db.refresh(intent)
        return intent

    async def update(self, db: AsyncSession, intent_id: int, data: dict) -> bool:
        """更新意图"""
        stmt = update(Intent).where(Intent.id == intent_id).values(**data)
        result = await db.execute(stmt)
        return result.rowcount > 0

    async def delete(self, db: AsyncSession, intent_id: int) -> bool:
        """删除意图"""
        stmt = delete(Intent).where(Intent.id == intent_id)
        result = await db.execute(stmt)
        return result.rowcount > 0
