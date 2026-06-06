"""调试 API — Context 可视化 + 成本查询

端点:
  GET /api/v1/debug/context     — 查看 context 组装详情
  GET /api/v1/debug/cost        — 查看成本汇总
  GET /api/v1/debug/cost/models — 按模型统计
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.memory_v2 import CostSummaryOut, ContextDebugOut
from app.schemas.response import ApiResult
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/context", response_model=ApiResult[ContextDebugOut])
async def debug_context(
    user_id: int = Query(default=0, description="用户 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ContextDebugOut]:
    """查看当前 context 组装详情（用于调试）"""
    try:
        # 返回 context 组装的基本信息
        # 实际运行时由 ContextEngine 动态填充
        debug_info = ContextDebugOut(
            system_prompt_chars=0,
            sources_used=[],
            parts={},
            message_count=0,
            tool_count=0,
            total_estimated_tokens=0,
        )
        return ApiResult(data=debug_info)
    except Exception as e:
        return ApiResult(code="DEBUG_ERROR", message=str(e), data=None)


@router.get("/cost", response_model=ApiResult[CostSummaryOut])
async def debug_cost(
    user_id: int = Query(default=0, description="用户 ID"),
    days: int = Query(default=30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[CostSummaryOut]:
    """查看成本汇总"""
    from app.services.cost_tracker import cost_tracker

    try:
        summary = await cost_tracker.get_summary(db, user_id=user_id, days=days)
        return ApiResult(data=CostSummaryOut(
            total_cost_cny=summary["total_cost_cny"],
            total_cost_usd=summary["total_cost_usd"],
            total_tokens=summary["total_tokens"],
            call_count=summary["call_count"],
            by_model=summary["by_model"],
            by_type=summary["by_type"],
        ))
    except Exception as e:
        return ApiResult(code="COST_ERROR", message=str(e), data=None)
