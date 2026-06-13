"""性能监控模型"""
from sqlalchemy import Column, Integer, Numeric, Index
from decimal import Decimal
from app.models.base import BaseModel


class PerformanceMetric(BaseModel):
    __tablename__ = "performance_metric"

    cpu_percent = Column(Numeric(5, 2), nullable=False, default=0.0, comment="CPU 使用率")
    memory_percent = Column(Numeric(5, 2), nullable=False, default=0.0, comment="内存使用率")
    memory_used_mb = Column(Integer, nullable=False, default=0, comment="已用内存 (MB)")
    disk_percent = Column(Numeric(5, 2), nullable=False, default=0.0, comment="磁盘使用率")
    disk_used_gb = Column(Integer, nullable=False, default=0, comment="已用磁盘 (GB)")
    gpu_percent = Column(Numeric(5, 2), nullable=False, default=Decimal('0.00'), comment="GPU 使用率 (0=无 GPU)")

    __table_args__ = (
        Index("idx_performance_metric_created_at", "created_at"),
    )
