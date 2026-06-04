"""工作流 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()


@router.get("", response_model=ApiPageResult)
async def list_workflows(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取工作流列表"""
    # TODO: 实现
    return ApiPageResult(data=[], total=0)


@router.post("", response_model=ApiResult)
async def create_workflow(
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """创建工作流"""
    # TODO: 实现
    return ApiResult(message="创建成功")


@router.get("/{workflow_id}", response_model=ApiResult)
async def get_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取工作流详情"""
    # TODO: 实现
    return ApiResult(data=None)


@router.put("/{workflow_id}", response_model=ApiResult)
async def update_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """更新工作流"""
    # TODO: 实现
    return ApiResult(message="更新成功")


@router.delete("/{workflow_id}", response_model=ApiResult)
async def delete_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除工作流"""
    # TODO: 实现
    return ApiResult(message="删除成功")


@router.post("/{workflow_id}/execute", response_model=ApiResult)
async def execute_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """执行工作流"""
    # TODO: 实现
    return ApiResult(data=None)


@router.get("/{workflow_id}/runs", response_model=ApiPageResult)
async def list_workflow_runs(
    workflow_id: int,
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取工作流运行记录"""
    # TODO: 实现
    return ApiPageResult(data=[], total=0)
