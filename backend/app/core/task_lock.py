"""Redis 分布式锁 + Watermark — 防止定时任务重复执行

设计:
  - distributed_lock: SET NX EX 原子锁，防并发 + 防重复
  - watermark: 记录上次处理位置，跳过已处理数据

使用场景:
  - check_idle_summaries: 锁(5min) + watermark(只处理 last_active > 上次扫描时间)
  - sleeptime_consolidation: 锁(24h)
  - memory_decay_sweep / observation_freshness_sweep: 天然幂等，无需加锁
"""
import time
from typing import Optional
from contextlib import asynccontextmanager

from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def distributed_lock(
    redis,
    key: str,
    ttl_seconds: int = 300,
    owner: str = "",
):
    """Redis 分布式锁（async context manager）

    基于 SET NX EX 原子操作。获取失败时静默跳过（不阻塞）。

    Args:
        redis: aioredis.Redis 实例
        key: 锁 key（建议前缀 dlock:）
        ttl_seconds: 锁过期时间（秒），防止死锁
        owner: 锁持有者标识（用于调试）

    Yields:
        True if lock acquired, False if skipped

    Example:
        async with distributed_lock(redis, "dlock:check_idle", 300) as acquired:
            if not acquired:
                return
            # 执行任务...
    """
    lock_key = f"dlock:{key}"
    owner = owner or f"pid-{time.time_ns()}"

    acquired = await redis.set(lock_key, owner, nx=True, ex=ttl_seconds)
    if not acquired:
        logger.debug(f"[task_lock] 锁被占用，跳过: {lock_key}")
        yield False
        return

    try:
        logger.debug(f"[task_lock] 获取锁: {lock_key} owner={owner}")
        yield True
    finally:
        # 只删自己的锁（防止误删其他实例的锁）
        current_owner = await redis.get(lock_key)
        if current_owner == owner:
            await redis.delete(lock_key)
            logger.debug(f"[task_lock] 释放锁: {lock_key}")


async def get_watermark(redis, task_name: str) -> Optional[str]:
    """获取任务水位线（上次处理的时间戳）

    Returns:
        ISO 格式时间字符串，或 None（首次执行）
    """
    data = await redis.get(f"watermark:{task_name}")
    return data


async def set_watermark(redis, task_name: str, value: str):
    """更新任务水位线

    Args:
        task_name: 任务标识
        value: 水位线值（通常为 ISO 时间戳）
    """
    await redis.set(f"watermark:{task_name}", value)
