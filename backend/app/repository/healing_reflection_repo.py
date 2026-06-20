"""自愈反思记忆 Repository — 封装 HealingReflection CRUD"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.healing_reflection import HealingReflection


class HealingReflectionRepository:
    """自愈反思记忆 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(HealingReflection)

    async def create(self, db: AsyncSession, data: dict) -> HealingReflection:
        """创建反思记录"""
        # 自动计算过期时间
        if "expired_at" not in data or data.get("expired_at") == "1970-01-01 00:00:00":
            ttl = data.get("ttl_seconds", 3600)
            data["expired_at"] = datetime.utcnow() + timedelta(seconds=ttl)
        return await self.mapper.create(db, data)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[HealingReflection]:
        return await self.mapper.find_by_id(db, id)

    async def find_active_by_user(
        self, db: AsyncSession, user_id: int,
        scope_tag: str = "", failure_type: str = "",
        limit: int = 5,
    ) -> List[HealingReflection]:
        """检索未过期的反思（按置信度降序）"""
        now = datetime.utcnow()
        filters = {
            "user_id": user_id,
            "is_deleted": 0,
        }
        if failure_type:
            filters["failure_type"] = failure_type
        # scope_tags 是 JSON 字段，精确匹配需要 JSON_CONTAINS，在应用层过滤
        results = await self.mapper.find_all(
            db, filters=filters, limit=limit * 2,
            order_by="confidence",
            order_desc=True,
        )
        # 应用层过滤: expired_at > now（mapper 不支持复杂比较）
        active = [r for r in results if r.expired_at and r.expired_at > now]
        return active[:limit]

    async def find_by_goal(
        self, db: AsyncSession, user_id: int,
        goal_definition: str, limit: int = 10,
    ) -> List[HealingReflection]:
        """按目标检索历史反思"""
        return await self.mapper.find_all(
            db,
            filters={"user_id": user_id, "goal_definition": goal_definition, "is_deleted": 0},
            limit=limit,
            order_by="created_at",
            order_desc=True,
        )

    async def mark_successful(self, db: AsyncSession, id: int) -> bool:
        """标记反思最终导致了成功"""
        updated = await self.mapper.update(db, id, {"was_successful": 1})
        return updated is not None

    async def increment_retry(self, db: AsyncSession, id: int) -> bool:
        """原子增加重试计数"""
        from sqlalchemy import update as sql_update
        stmt = (
            sql_update(HealingReflection)
            .where(HealingReflection.id == id)
            .values(retry_count=HealingReflection.retry_count + 1, updated_at=datetime.utcnow())
        )
        result = await db.execute(stmt)
        return result.rowcount > 0

    async def cleanup_expired(self, db: AsyncSession) -> int:
        """清理过期反思（软删除）—— 不 commit，由调用方管理事务"""
        now = datetime.utcnow()
        from sqlalchemy import update as sql_update
        stmt = (
            sql_update(HealingReflection)
            .where(
                and_(
                    HealingReflection.expired_at < now,
                    HealingReflection.is_deleted == 0,
                )
            )
            .values(is_deleted=1, updated_at=now)
        )
        result = await db.execute(stmt)
        return result.rowcount

    async def count_by_user(self, db: AsyncSession, user_id: int) -> int:
        return await self.mapper.count(db, filters={"user_id": user_id, "is_deleted": 0})

    async def get_success_rate(self, db: AsyncSession, user_id: int) -> dict:
        """统计各类型反思的成功率"""
        from sqlalchemy import func
        stmt = (
            select(
                HealingReflection.failure_type,
                func.count().label("total"),
                func.sum(HealingReflection.was_successful).label("successful"),
            )
            .where(
                and_(
                    HealingReflection.user_id == user_id,
                    HealingReflection.is_deleted == 0,
                )
            )
            .group_by(HealingReflection.failure_type)
        )
        result = await db.execute(stmt)
        rows = result.all()
        stats = {}
        for row in rows:
            total = row.total or 0
            successful = row.successful or 0
            stats[row.failure_type] = {
                "total": total,
                "successful": successful,
                "success_rate": round(successful / total * 100, 1) if total > 0 else 0,
            }
        return stats
