"""工作流 Repository — 封装 Workflow / WorkflowRun / WorkflowStepRun CRUD"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.workflow import Workflow, WorkflowRun, WorkflowStepRun


class WorkflowRepository:
    """工作流 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(Workflow)
        self.run_mapper = MySQLMapper(WorkflowRun)
        self.step_mapper = MySQLMapper(WorkflowStepRun)

    # ── Workflow CRUD ────────────────────────────────────

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[Workflow]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        enabled: Optional[int] = None,
    ) -> List[Workflow]:
        filters = {}
        if enabled is not None:
            filters["is_enabled"] = enabled
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, enabled: Optional[int] = None) -> int:
        filters = {}
        if enabled is not None:
            filters["is_enabled"] = enabled
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> Workflow:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[Workflow]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def set_enabled(self, db: AsyncSession, id: int, enabled: int) -> bool:
        result = await self.mapper.update(db, id, {"is_enabled": enabled})
        return result is not None

    # ── WorkflowRun ──────────────────────────────────────

    async def create_run(self, db: AsyncSession, data: dict) -> WorkflowRun:
        return await self.run_mapper.create(db, data)

    async def update_run(self, db: AsyncSession, run_id: int, data: dict) -> Optional[WorkflowRun]:
        return await self.run_mapper.update(db, run_id, data)

    async def find_runs(
        self, db: AsyncSession, workflow_id: int,
        offset: int = 0, limit: int = 20,
    ) -> List[WorkflowRun]:
        return await self.run_mapper.find_all(
            db, filters={"workflow_id": workflow_id}, offset=offset, limit=limit,
        )

    async def count_runs(self, db: AsyncSession, workflow_id: int) -> int:
        return await self.run_mapper.count(db, filters={"workflow_id": workflow_id})

    async def find_run_by_id(self, db: AsyncSession, run_id: int) -> Optional[WorkflowRun]:
        return await self.run_mapper.find_by_id(db, run_id)

    # ── WorkflowStepRun ──────────────────────────────────

    async def create_step_run(self, db: AsyncSession, data: dict) -> WorkflowStepRun:
        return await self.step_mapper.create(db, data)

    async def update_step_run(self, db: AsyncSession, step_id: int, data: dict) -> Optional[WorkflowStepRun]:
        return await self.step_mapper.update(db, step_id, data)

    async def find_step_runs(self, db: AsyncSession, run_id: int) -> List[WorkflowStepRun]:
        return await self.step_mapper.find_all(
            db, filters={"run_id": run_id}, offset=0, limit=100,
        )
