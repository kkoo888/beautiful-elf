"""性能监控 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repository.performance_repo import PerformanceRepo
from app.services.performance_service import PerformanceService
from app.schemas.response import success

router = APIRouter()


def _get_service() -> PerformanceService:
    return PerformanceService(PerformanceRepo())


@router.get("/current")
async def get_current_status(service: PerformanceService = Depends(_get_service)):
    """获取当前系统状态"""
    data = await service.get_current_status()
    return success(data.model_dump())


@router.get("/metrics")
async def get_metrics(
    limit: int = Query(default=60, ge=1, le=360, description="返回条数"),
    db: AsyncSession = Depends(get_db),
    service: PerformanceService = Depends(_get_service),
):
    """获取历史采样数据"""
    data = await service.get_metrics(db, limit=limit)
    return success([item.model_dump() for item in data])


@router.post("/collect")
async def manual_collect(
    db: AsyncSession = Depends(get_db),
    service: PerformanceService = Depends(_get_service),
):
    """手动触发一次采样（开发用）"""
    record = await service.collect_and_store(db)
    return success(record.model_dump())
