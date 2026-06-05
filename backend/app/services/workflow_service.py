"""工作流 Service — 封装工作流 CRUD + 执行

遵循规范:
  - 分层架构: service 调用 repository
  - 统一异常: RecordNotFoundError
  - ORM → Pydantic: _to_out 方法
"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.workflow_repo import WorkflowRepository
from app.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowOut,
    WorkflowRunOut, WorkflowStepRunOut,
)
from app.core.exceptions import RecordNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowService:
    """工作流业务服务"""

    def __init__(self):
        self.repo = WorkflowRepository()

    # ── Workflow CRUD ────────────────────────────────────

    async def list_workflows(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        enabled: Optional[int] = None,
    ) -> Tuple[List[WorkflowOut], int]:
        """获取工作流列表"""
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, enabled=enabled)
        total = await self.repo.count(db, enabled=enabled)
        return [self._to_out(i) for i in items], total

    async def get_workflow(self, db: AsyncSession, workflow_id: int) -> WorkflowOut:
        """获取工作流详情"""
        item = await self.repo.find_by_id(db, workflow_id)
        if not item:
            raise RecordNotFoundError("工作流不存在")
        return self._to_out(item)

    async def create_workflow(self, db: AsyncSession, data: WorkflowCreate) -> WorkflowOut:
        """创建工作流"""
        # 校验 DAG 结构
        self._validate_dag(data.dag_json)

        item = await self.repo.create(db, {
            "name": data.name,
            "description": data.description,
            "dag_json": data.dag_json,
            "trigger_type": data.trigger_type,
            "cron_expr": data.cron_expr,
            "event_trigger": data.event_trigger,
            "is_enabled": 1,
            "version": 1,
        })
        return self._to_out(item)

    async def update_workflow(self, db: AsyncSession, workflow_id: int, data: WorkflowUpdate) -> WorkflowOut:
        """更新工作流"""
        item = await self.repo.find_by_id(db, workflow_id)
        if not item:
            raise RecordNotFoundError("工作流不存在")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_out(item)

        # 校验 DAG 结构
        if "dag_json" in update_data and update_data["dag_json"]:
            self._validate_dag(update_data["dag_json"])
            update_data["version"] = item.version + 1

        updated = await self.repo.update(db, workflow_id, update_data)
        return self._to_out(updated)

    async def delete_workflow(self, db: AsyncSession, workflow_id: int) -> bool:
        """删除工作流"""
        item = await self.repo.find_by_id(db, workflow_id)
        if not item:
            raise RecordNotFoundError("工作流不存在")
        return await self.repo.soft_delete(db, workflow_id)

    async def enable_workflow(self, db: AsyncSession, workflow_id: int) -> WorkflowOut:
        """启用工作流"""
        item = await self.repo.find_by_id(db, workflow_id)
        if not item:
            raise RecordNotFoundError("工作流不存在")
        await self.repo.set_enabled(db, workflow_id, 1)
        return self._to_out(await self.repo.find_by_id(db, workflow_id))

    async def disable_workflow(self, db: AsyncSession, workflow_id: int) -> WorkflowOut:
        """禁用工作流"""
        item = await self.repo.find_by_id(db, workflow_id)
        if not item:
            raise RecordNotFoundError("工作流不存在")
        await self.repo.set_enabled(db, workflow_id, 0)
        return self._to_out(await self.repo.find_by_id(db, workflow_id))

    # ── 执行 ─────────────────────────────────────────────

    async def execute_workflow(
        self, db: AsyncSession, workflow_id: int, input_data: dict = None,
    ) -> WorkflowRunOut:
        """执行工作流"""
        from app.agent.workflow_engine import workflow_engine

        item = await self.repo.find_by_id(db, workflow_id)
        if not item:
            raise RecordNotFoundError("工作流不存在")

        result = await workflow_engine.execute(db, workflow_id, input_data)

        # 获取运行记录
        runs = await self.repo.find_runs(db, workflow_id, offset=0, limit=1)
        if not runs:
            raise RecordNotFoundError("运行记录不存在")

        return await self._run_to_out(db, runs[0])

    # ── 运行记录 ─────────────────────────────────────────

    async def list_runs(
        self, db: AsyncSession, workflow_id: int, page: int = 1, page_size: int = 20,
    ) -> Tuple[List[WorkflowRunOut], int]:
        """获取运行记录列表"""
        offset = (page - 1) * page_size
        items = await self.repo.find_runs(db, workflow_id, offset=offset, limit=page_size)
        total = await self.repo.count_runs(db, workflow_id)

        out_list = []
        for item in items:
            out_list.append(await self._run_to_out(db, item))

        return out_list, total

    # ── 内部方法 ─────────────────────────────────────────

    def _validate_dag(self, dag: dict):
        """校验 DAG 结构"""
        nodes = dag.get("nodes")
        if not nodes or not isinstance(nodes, dict):
            raise ValueError("DAG 必须包含 nodes 字段（dict）")

        edges = dag.get("edges", [])
        if not isinstance(edges, list):
            raise ValueError("edges 必须是 list")

        # 校验边的端点都存在于节点中
        for edge in edges:
            if edge.get("from") not in nodes:
                raise ValueError(f"边的起点 '{edge.get('from')}' 不存在于节点中")
            if edge.get("to") not in nodes:
                raise ValueError(f"边的终点 '{edge.get('to')}' 不存在于节点中")

    async def _run_to_out(self, db, run) -> WorkflowRunOut:
        """运行记录 → Pydantic（含步骤详情）"""
        steps = await self.repo.find_step_runs(db, run.id)
        step_outs = [WorkflowStepRunOut.model_validate(s) for s in steps]

        out = WorkflowRunOut.model_validate(run)
        out.steps = step_outs
        return out

    @staticmethod
    def _to_out(item) -> WorkflowOut:
        """ORM → Pydantic"""
        return WorkflowOut.model_validate(item)


# ── 全局单例 ──────────────────────────────────────────────

workflow_service = WorkflowService()
