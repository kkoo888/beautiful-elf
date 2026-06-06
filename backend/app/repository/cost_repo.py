"""成本追踪 Repository"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.mappers.base import MySQLMapper
from app.models.cost_tracking import CostRecord


class CostRepository:
    """成本追踪 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(CostRecord)

    async def create(self, db: AsyncSession, data: dict) -> CostRecord:
        return await self.mapper.create(db, data)

    async def summary_by_user(
        self, db: AsyncSession, user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """按用户汇总成本"""
        stmt = select(
            func.sum(CostRecord.cost_cny).label("total_cny"),
            func.sum(CostRecord.cost_usd).label("total_usd"),
            func.sum(CostRecord.total_tokens).label("total_tokens"),
            func.count(CostRecord.id).label("call_count"),
        ).where(
            CostRecord.user_id == user_id,
            CostRecord.is_deleted == 0,
        )
        if start_date:
            stmt = stmt.where(CostRecord.created_at >= start_date)
        if end_date:
            stmt = stmt.where(CostRecord.created_at <= end_date)

        result = await db.execute(stmt)
        row = result.one()
        return {
            "total_cny": float(row.total_cny or 0),
            "total_usd": float(row.total_usd or 0),
            "total_tokens": int(row.total_tokens or 0),
            "call_count": int(row.call_count or 0),
        }

    async def summary_by_model(
        self, db: AsyncSession, user_id: int,
        days: int = 30,
    ) -> List[dict]:
        """按模型汇总（最近 N 天）"""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                CostRecord.model_name,
                func.sum(CostRecord.total_tokens).label("total_tokens"),
                func.sum(CostRecord.cost_cny).label("total_cny"),
                func.count(CostRecord.id).label("call_count"),
            )
            .where(
                CostRecord.user_id == user_id,
                CostRecord.is_deleted == 0,
                CostRecord.created_at >= since,
            )
            .group_by(CostRecord.model_name)
            .order_by(func.sum(CostRecord.cost_cny).desc())
        )
        result = await db.execute(stmt)
        return [
            {
                "model_name": row.model_name,
                "total_tokens": int(row.total_tokens or 0),
                "total_cny": float(row.total_cny or 0),
                "call_count": int(row.call_count or 0),
            }
            for row in result.all()
        ]

    async def summary_by_type(
        self, db: AsyncSession, user_id: int,
        days: int = 30,
    ) -> List[dict]:
        """按调用类型汇总"""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                CostRecord.call_type,
                func.sum(CostRecord.total_tokens).label("total_tokens"),
                func.sum(CostRecord.cost_cny).label("total_cny"),
                func.count(CostRecord.id).label("call_count"),
            )
            .where(
                CostRecord.user_id == user_id,
                CostRecord.is_deleted == 0,
                CostRecord.created_at >= since,
            )
            .group_by(CostRecord.call_type)
        )
        result = await db.execute(stmt)
        return [
            {
                "call_type": row.call_type,
                "total_tokens": int(row.total_tokens or 0),
                "total_cny": float(row.total_cny or 0),
                "call_count": int(row.call_count or 0),
            }
            for row in result.all()
        ]
