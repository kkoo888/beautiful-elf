"""工作流 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.workflow_service import workflow_service
from app.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowOut, WorkflowRunOut,
)
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=ApiPageResult)
async def list_workflows(
    pagination: PaginationParams = Depends(get_pagination),
    enabled: int | None = Query(default=None, description="启用状态筛选"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取工作流列表"""
    items, total = await workflow_service.list_workflows(
        db, page=pagination.page, page_size=pagination.page_size, enabled=enabled,
    )
    return ApiPageResult(data=items, total=total)


@router.get("/{workflow_id}", response_model=ApiResult[WorkflowOut])
async def get_workflow(
    workflow_id: int = Path(..., description="工作流 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[WorkflowOut]:
    """获取工作流详情"""
    try:
        item = await workflow_service.get_workflow(db, workflow_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("WORKFLOW_NOT_FOUND", str(e), "请检查工作流 ID")


@router.post("", response_model=ApiResult[WorkflowOut])
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[WorkflowOut]:
    """创建工作流"""
    try:
        item = await workflow_service.create_workflow(db, data)
        return ApiResult(data=item)
    except ValueError as e:
        return api_error("WORKFLOW_VALIDATION", str(e), "请检查 DAG 定义")
    except Exception as e:
        logger.error(f"创建工作流失败: {e}", exc_info=True)
        return api_error("WORKFLOW_INTERNAL_ERROR", str(e), "创建工作流失败，请稍后重试")


@router.put("/{workflow_id}", response_model=ApiResult[WorkflowOut])
async def update_workflow(
    workflow_id: int = Path(..., description="工作流 ID"),
    data: WorkflowUpdate = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[WorkflowOut]:
    """更新工作流"""
    try:
        item = await workflow_service.update_workflow(db, workflow_id, data)
        return ApiResult(data=item)
    except ValueError as e:
        return api_error("WORKFLOW_VALIDATION", str(e), "请检查 DAG 定义")
    except Exception as e:
        return api_error("WORKFLOW_NOT_FOUND", str(e), "请检查工作流 ID")


@router.delete("/{workflow_id}", response_model=ApiResult)
async def delete_workflow(
    workflow_id: int = Path(..., description="工作流 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除工作流"""
    try:
        await workflow_service.delete_workflow(db, workflow_id)
        return ApiResult(message="删除成功")
    except Exception as e:
        return api_error("WORKFLOW_NOT_FOUND", str(e), "请检查工作流 ID")


@router.patch("/{workflow_id}/enable", response_model=ApiResult[WorkflowOut])
async def enable_workflow(
    workflow_id: int = Path(..., description="工作流 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[WorkflowOut]:
    """启用工作流"""
    try:
        item = await workflow_service.enable_workflow(db, workflow_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("WORKFLOW_NOT_FOUND", str(e), "请检查工作流 ID")


@router.patch("/{workflow_id}/disable", response_model=ApiResult[WorkflowOut])
async def disable_workflow(
    workflow_id: int = Path(..., description="工作流 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[WorkflowOut]:
    """禁用工作流"""
    try:
        item = await workflow_service.disable_workflow(db, workflow_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("WORKFLOW_NOT_FOUND", str(e), "请检查工作流 ID")


@router.post("/{workflow_id}/execute", response_model=ApiResult[WorkflowRunOut])
async def execute_workflow(
    workflow_id: int = Path(..., description="工作流 ID"),
    input_data: dict | None = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[WorkflowRunOut]:
    """执行工作流"""
    try:
        result = await workflow_service.execute_workflow(db, workflow_id, input_data)
        return ApiResult(data=result)
    except Exception as e:
        logger.error(f"执行工作流失败: {e}", exc_info=True)
        return api_error("WORKFLOW_INTERNAL_ERROR", str(e), "工作流执行失败，请检查配置")


@router.get("/{workflow_id}/runs", response_model=ApiPageResult)
async def list_workflow_runs(
    workflow_id: int = Path(..., description="工作流 ID"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取工作流运行记录"""
    items, total = await workflow_service.list_runs(
        db, workflow_id, page=pagination.page, page_size=pagination.page_size,
    )
    return ApiPageResult(data=items, total=total)
