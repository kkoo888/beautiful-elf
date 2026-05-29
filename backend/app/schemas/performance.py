"""性能监控 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PerformanceMetricOut(BaseModel):
    """性能指标输出"""
    id: int
    cpu_percent: float
    memory_percent: float
    memory_used_mb: int
    disk_percent: float
    disk_used_gb: int
    gpu_percent: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CurrentStatusOut(BaseModel):
    """当前系统状态"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: int
    memory_total_mb: int
    disk_percent: float
    disk_used_gb: int
    disk_total_gb: int
    gpu_percent: Optional[float] = None
    uptime_seconds: float
