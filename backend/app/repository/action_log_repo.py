"""行为日志 Repository"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import ActionLog


class ActionLogRepository:
    def __init__(self):
        self.mapper = MySQLMapper(ActionLog)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[ActionLog]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        module: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[ActionLog]:
        try:
            stmt = select(ActionLog).where(ActionLog.is_deleted == 0)
            if module:
                stmt = stmt.where(ActionLog.module == module)
            if action:
                stmt = stmt.where(ActionLog.action == action)
            if start_time:
                stmt = stmt.where(ActionLog.created_at >= start_time)
            if end_time:
                stmt = stmt.where(ActionLog.created_at <= end_time)
            stmt = stmt.order_by(ActionLog.created_at.desc())
            stmt = stmt.offset(offset).limit(limit)
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            from app.core.exceptions import StorageError
            raise StorageError(f"查询列表失败: {e}")

    async def count(
        self,
        db: AsyncSession,
        module: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        try:
            from sqlalchemy import func
            stmt = select(func.count()).select_from(ActionLog).where(ActionLog.is_deleted == 0)
            if module:
                stmt = stmt.where(ActionLog.module == module)
            if action:
                stmt = stmt.where(ActionLog.action == action)
            if start_time:
                stmt = stmt.where(ActionLog.created_at >= start_time)
            if end_time:
                stmt = stmt.where(ActionLog.created_at <= end_time)
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            from app.core.exceptions import StorageError
            raise StorageError(f"统计失败: {e}")

    async def create(self, db: AsyncSession, data: dict) -> ActionLog:
        return await self.mapper.create(db, data)

    async def cleanup_old(self, db: AsyncSession, days: int = 7) -> int:
        """物理删除 N 天前的日志记录"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            stmt = delete(ActionLog).where(ActionLog.created_at < cutoff)
            result = await db.execute(stmt)
            await db.flush()
            return result.rowcount
        except Exception as e:
            from app.core.exceptions import StorageError
            raise StorageError(f"清理日志失败: {e}")
