"""性能监控 Service"""
import asyncio
import platform
import time
from typing import List

import psutil
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repository.performance_repo import PerformanceRepo
from app.schemas.performance import PerformanceMetricOut, CurrentStatusOut

logger = get_logger(__name__)

MAX_SAMPLES = 360


def _disk_path() -> str:
    """获取磁盘采集路径（跨平台）"""
    if platform.system() == "Windows":
        return "C:\\"
    return "/"


class PerformanceService:
    """性能监控业务层"""

    def __init__(self, repo: PerformanceRepo = None):
        self.repo = repo or PerformanceRepo()

    def _collect_sync(self) -> dict:
        """同步采集系统指标（在线程中运行）"""
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()

        # 磁盘采集（跨平台 + 容错）
        disk_percent = 0.0
        disk_used_gb = 0
        disk_total_gb = 0
        try:
            disk = psutil.disk_usage(_disk_path())
            disk_percent = round(disk.percent, 2)
            disk_used_gb = disk.used // (1024 * 1024 * 1024)
            disk_total_gb = disk.total // (1024 * 1024 * 1024)
        except OSError as e:
            logger.warning(f"磁盘采集失败: {e}")

        # 尝试采集 GPU（可选）
        gpu_percent = None
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_percent = round(gpus[0].load * 100, 2)
        except Exception:
            pass

        return {
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory.percent, 2),
            "memory_used_mb": memory.used // (1024 * 1024),
            "memory_total_mb": memory.total // (1024 * 1024),
            "disk_percent": disk_percent,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "gpu_percent": gpu_percent,
            "uptime_seconds": time.time() - psutil.boot_time(),
        }

    async def collect_system_metrics(self) -> dict:
        """异步采集系统指标（不阻塞事件循环）"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._collect_sync)

    async def get_current_status(self) -> CurrentStatusOut:
        """获取当前系统状态（不入库）"""
        data = await self.collect_system_metrics()
        return CurrentStatusOut(**data)

    async def collect_and_store(self, db: AsyncSession) -> PerformanceMetricOut:
        """采集一次并写入数据库，超出上限自动清理"""
        metrics = await self.collect_system_metrics()

        record = await self.repo.create(
            db,
            {
                "cpu_percent": metrics["cpu_percent"],
                "memory_percent": metrics["memory_percent"],
                "memory_used_mb": metrics["memory_used_mb"],
                "disk_percent": metrics["disk_percent"],
                "disk_used_gb": metrics["disk_used_gb"],
                "gpu_percent": metrics["gpu_percent"],
            },
        )

        # 超过上限时清理旧数据
        total = await self.repo.count_all(db)
        if total > MAX_SAMPLES:
            deleted = await self.repo.delete_oldest(db, keep=MAX_SAMPLES)
            if deleted > 0:
                logger.info(f"清理旧采样数据 {deleted} 条，保留 {MAX_SAMPLES} 条")

        return PerformanceMetricOut.model_validate(record)

    async def get_metrics(
        self, db: AsyncSession, limit: int = 60
    ) -> List[PerformanceMetricOut]:
        """获取历史采样数据"""
        records = await self.repo.get_latest(db, limit=limit)
        return [PerformanceMetricOut.model_validate(r) for r in records]
