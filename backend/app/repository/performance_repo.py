"""性能监控 Repository"""
from typing import List
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PerformanceMetric
from app.mappers.base import MySQLMapper


class PerformanceRepo:
    """性能指标数据访问层"""

    def __init__(self):
        self.mapper = MySQLMapper(PerformanceMetric)

    async def create(self, db: AsyncSession, data: dict) -> PerformanceMetric:
        """写入一条采样记录"""
        return await self.mapper.create(db, data)

    async def get_latest(
        self, db: AsyncSession, limit: int = 60
    ) -> List[PerformanceMetric]:
        """获取最近 N 条采样数据（按时间倒序）"""
        return await self.mapper.find_all(
            db, offset=0, limit=limit, order_by=PerformanceMetric.created_at.desc()
        )

    async def count_all(self, db: AsyncSession) -> int:
        """统计总采样数"""
        return await self.mapper.count(db)

    async def delete_oldest(self, db: AsyncSession, keep: int = 360) -> int:
        """保留最新 keep 条，软删除超出的旧数据"""
        try:
            total = await self.count_all(db)
            if total <= keep:
                return 0

            # 找到第 keep 条的 created_at 作为分界线
            subq = (
                select(PerformanceMetric.created_at)
                .where(PerformanceMetric.deleted == 0)
                .order_by(PerformanceMetric.created_at.desc())
                .offset(keep - 1)
                .limit(1)
                .scalar_subquery()
            )
            stmt = (
                sa_update(PerformanceMetric)
                .where(
                    PerformanceMetric.deleted == 0,
                    PerformanceMetric.created_at < subq,
                )
                .values(deleted=1)
            )
            result = await db.execute(stmt)
            await db.flush()
            return result.rowcount
        except Exception:
            return 0
