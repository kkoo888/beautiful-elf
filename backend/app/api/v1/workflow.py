"""工作流 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination

router = APIRouter()


@router.get("")
async def list_workflows(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    """获取工作流列表"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": {"items": [], "total": 0}}


@router.post("")
async def create_workflow(
    db: AsyncSession = Depends(get_db),
):
    """创建工作流"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": None}


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取工作流详情"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": None}


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """更新工作流"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": None}


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除工作流"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": None}


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
):
    """执行工作流"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": None}


@router.get("/{workflow_id}/runs")
async def list_workflow_runs(
    workflow_id: int,
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    """获取工作流运行记录"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": {"items": [], "total": 0}}
