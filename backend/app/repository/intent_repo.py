"""意图 Repository — 封装 Intent / IntentUsage CRUD"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.intent import Intent, IntentUsage


class IntentRepository:
    """意图 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(Intent)
        self.usage_mapper = MySQLMapper(IntentUsage)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Intent]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 50,
        enabled: Optional[int] = None,
    ) -> List[Intent]:
        filters = {}
        if enabled is not None:
            filters["is_enabled"] = enabled
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, enabled: Optional[int] = None) -> int:
        filters = {}
        if enabled is not None:
            filters["is_enabled"] = enabled
        return await self.mapper.count(db, filters=filters)

    async def find_all_enabled(self, db: AsyncSession) -> List[Intent]:
        """获取所有启用的意图（同步向量用）"""
        return await self.mapper.find_all(db, filters={"is_enabled": 1}, offset=0, limit=1000)

    async def create(self, db: AsyncSession, data: dict) -> Intent:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[Intent]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def set_enabled(self, db: AsyncSession, id: int, enabled: int) -> bool:
        """启用/禁用意图"""
        result = await self.mapper.update(db, id, {"is_enabled": enabled})
        return result is not None

    async def set_qdrant_point(self, db: AsyncSession, id: int, point_id: str) -> bool:
        """更新 Qdrant 向量 ID"""
        result = await self.mapper.update(db, id, {"qdrant_point_id": point_id})
        return result is not None

    # ── 命中统计 ─────────────────────────────────────────

    async def record_hit(self, db: AsyncSession, intent_id: int, confidence: float) -> IntentUsage:
        """记录意图命中"""
        stmt = select(IntentUsage).where(IntentUsage.intent_id == intent_id)
        result = await db.execute(stmt)
        usage = result.scalar_one_or_none()

        if not usage:
            return await self.usage_mapper.create(db, {
                "intent_id": intent_id,
                "hit_count": 1,
                "avg_confidence": confidence,
                "last_hit_at": datetime.now(),
            })

        new_count = usage.hit_count + 1
        new_avg = float((usage.avg_confidence * usage.hit_count + confidence) / new_count)

        stmt = (
            update(IntentUsage)
            .where(IntentUsage.id == usage.id)
            .values(
                hit_count=new_count,
                avg_confidence=new_avg,
                last_hit_at=datetime.now(),
            )
        )
        await db.execute(stmt)
        await db.flush()
        return await self.usage_mapper.find_by_id(db, usage.id)

    async def get_usage(self, db: AsyncSession, intent_id: int) -> Optional[IntentUsage]:
        """获取意图使用统计"""
        stmt = select(IntentUsage).where(IntentUsage.intent_id == intent_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
