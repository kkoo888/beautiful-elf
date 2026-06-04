"""行为日志 Service"""
from typing import List, Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.action_log_repo import ActionLogRepository
from app.schemas.action_log import ActionLogCreate, ActionLogOut


class ActionLogService:
    def __init__(self):
        self.repo = ActionLogRepository()

    @staticmethod
    def _to_out(item) -> ActionLogOut:
        """ORM → Pydantic 模型"""
        return ActionLogOut.model_validate(item)

    async def create(self, db: AsyncSession, data: ActionLogCreate) -> ActionLogOut:
        item = await self.repo.create(db, data.model_dump())
        return self._to_out(item)

    async def list(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        module: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Tuple[List[ActionLogOut], int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(
            db,
            offset=offset,
            limit=page_size,
            module=module,
            action=action,
            start_time=start_time,
            end_time=end_time,
        )
        total = await self.repo.count(
            db, module=module, action=action,
            start_time=start_time, end_time=end_time,
        )
        return [self._to_out(i) for i in items], total

    async def cleanup_old(self, db: AsyncSession, days: int = 7) -> int:
        """清理 N 天前的日志"""
        return await self.repo.cleanup_old(db, days)
