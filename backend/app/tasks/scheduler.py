"""Asyncio 背景定时调度器 — 替代 Celery Beat

设计:
  - 每个定时任务一个 asyncio.Task，循环 sleep + 执行
  - 启动时创建，关闭时 cancel + await
  - 异常不退出循环，记录日志后继续下一轮
  - 天然防重: 单线程 asyncio，同一任务不会并发执行

用法:
  在 lifespan startup 中调用 start_scheduler()
  在 lifespan shutdown 中调用 stop_scheduler()
"""
import asyncio
from typing import Dict, Callable, Awaitable, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

_tasks: Dict[str, asyncio.Task] = {}


async def _loop(name: str, func: Callable[[], Awaitable[None]], interval: int):
    """通用定时循环 — 异常不退出，cancel 时优雅退出"""
    logger.info(f"[scheduler] {name} 启动 (间隔 {interval}s)")
    while True:
        try:
            await func()
        except asyncio.CancelledError:
            logger.info(f"[scheduler] {name} 已停止")
            return
        except Exception as e:
            logger.warning(f"[scheduler] {name} 执行异常: {e}", exc_info=True)
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info(f"[scheduler] {name} 已停止")
            return


def start_scheduler():
    """启动所有定时任务（在 lifespan startup 中调用）"""
    from app.tasks.memory_tasks import (
        check_idle_summaries,
        process_summary_queue,
        memory_decay_sweep,
        observation_freshness_sweep,
        sleeptime_consolidation,
    )

    schedule = {
        "check_idle_summaries": (check_idle_summaries, 1800),      # 30 分钟
        "process_summary_queue": (process_summary_queue, 600),     # 10 分钟
        "memory_decay_sweep": (memory_decay_sweep, 21600),         # 6 小时
        "observation_freshness_sweep": (observation_freshness_sweep, 604800),  # 7 天
        "sleeptime_consolidation": (sleeptime_consolidation, 86400),           # 24 小时
    }

    for name, (func, interval) in schedule.items():
        task = asyncio.create_task(_loop(name, func, interval), name=f"scheduler:{name}")
        _tasks[name] = task
        logger.info(f"[scheduler] {name} 已注册")


async def stop_scheduler():
    """停止所有定时任务（在 lifespan shutdown 中调用）"""
    for name, task in _tasks.items():
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    _tasks.clear()
    logger.info("[scheduler] 全部定时任务已停止")
