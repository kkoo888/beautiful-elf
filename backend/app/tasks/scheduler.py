"""Asyncio 背景定时调度器 — 替代 Celery Beat

设计:
  - 每个定时任务一个 asyncio.Task，循环 sleep + 执行
  - 启动时创建，关闭时 cancel + await
  - 异常不退出循环，记录日志后继续下一轮
  - 天然防重: 单线程 asyncio，同一任务不会并发执行
  - 支持运行时启停控制（通过 scheduler_control API）
  - 开关状态 + 间隔配置从 memory_setting 表读取

用法:
  在 lifespan startup 中调用 start_scheduler(settings=[...])
  在 lifespan shutdown 中调用 stop_scheduler()
"""
import asyncio
from typing import Dict, Callable, Awaitable, Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_tasks: Dict[str, asyncio.Task] = {}
_enabled: Dict[str, bool] = {}
_schedule_config: Dict[str, tuple[Callable, int]] = {}

# key → 中文标签（用于 API 返回）
TASK_LABELS: Dict[str, str] = {
    "scheduler_check_idle_summaries": "空闲会话归档",
    "scheduler_process_summary_queue": "摘要队列消费",
    "scheduler_memory_decay_sweep": "记忆衰减扫描",
    "scheduler_observation_freshness_sweep": "观察新鲜度衰减",
    "scheduler_sleeptime_consolidation": "SleepTime 深度整理",
}

# 默认间隔（仅在 DB 无数据时降级使用）
_DEFAULT_INTERVALS: Dict[str, int] = {
    "scheduler_check_idle_summaries": 1800,
    "scheduler_process_summary_queue": 600,
    "scheduler_memory_decay_sweep": 21600,
    "scheduler_observation_freshness_sweep": 604800,
    "scheduler_sleeptime_consolidation": 86400,
}


async def _loop(name: str, func: Callable[[], Awaitable[None]], interval: int):
    """通用定时循环 — 异常不退出，cancel 时优雅退出"""
    logger.info(f"[scheduler] {name} 启动 (间隔 {interval}s)")
    while True:
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info(f"[scheduler] {name} 已停止")
            return

        try:
            await func()
        except asyncio.CancelledError:
            logger.info(f"[scheduler] {name} 已停止")
            return
        except Exception as e:
            logger.warning(f"[scheduler] {name} 执行异常: {e}", exc_info=True)


def _get_func_map() -> Dict[str, Callable]:
    """懒加载 key → function 映射（避免顶层 import 循环）"""
    from app.tasks.memory_tasks import (
        check_idle_summaries,
        process_summary_queue,
        memory_decay_sweep,
        observation_freshness_sweep,
        sleeptime_consolidation,
    )
    return {
        "scheduler_check_idle_summaries": check_idle_summaries,
        "scheduler_process_summary_queue": process_summary_queue,
        "scheduler_memory_decay_sweep": memory_decay_sweep,
        "scheduler_observation_freshness_sweep": observation_freshness_sweep,
        "scheduler_sleeptime_consolidation": sleeptime_consolidation,
    }


def start_scheduler(settings: list[dict[str, Any]] | None = None):
    """启动所有定时任务（在 lifespan startup 中调用）

    Args:
        settings: 从 memory_setting 表读取的配置列表，每项含
                  setting_key / is_enabled / interval_seconds。
                  为 None 或空时降级为全启用 + 默认间隔。
    """
    func_map = _get_func_map()

    if not settings:
        # 降级：DB 无数据时全启用 + 默认间隔
        for key, func in func_map.items():
            interval = _DEFAULT_INTERVALS.get(key, 3600)
            _schedule_config[key] = (func, interval)
            _enabled[key] = True
            _start_task(key)
            logger.info(f"[scheduler] {key} 已注册 (默认间隔 {interval}s)")
        return

    for s in settings:
        key = s["setting_key"]
        func = func_map.get(key)
        if not func:
            logger.warning(f"[scheduler] 未知任务 key: {key}，跳过")
            continue
        interval = s.get("interval_seconds") or _DEFAULT_INTERVALS.get(key, 3600)
        enabled = bool(s.get("is_enabled", True))
        _schedule_config[key] = (func, interval)
        _enabled[key] = enabled
        if enabled:
            _start_task(key)
        logger.info(f"[scheduler] {key} 已注册 (enabled={enabled}, interval={interval}s)")


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


def get_all_tasks_status() -> list[dict[str, Any]]:
    """获取所有定时任务状态"""
    result = []
    for name in _schedule_config:
        func, interval = _schedule_config[name]
        result.append({
            "name": name,
            "label": TASK_LABELS.get(name, name),
            "enabled": _enabled.get(name, True),
            "interval": interval,
            "intervalLabel": _format_interval(interval),
        })
    return result


def set_task_enabled(name: str, enabled: bool) -> bool:
    """设置任务启停状态 — 停止时 cancel asyncio.Task，启用时重新创建"""
    if name not in _schedule_config:
        return False

    _enabled[name] = enabled

    if enabled:
        _start_task(name)
    else:
        _cancel_task(name)

    state = "启用" if enabled else "停止"
    logger.info(f"[scheduler] {name} 已{state}")
    return True


def _start_task(name: str):
    """启动单个定时任务"""
    func, interval = _schedule_config[name]
    if name in _tasks and not _tasks[name].done():
        return
    task = asyncio.create_task(_loop(name, func, interval), name=f"scheduler:{name}")
    _tasks[name] = task


def _cancel_task(name: str):
    """停止单个定时任务"""
    task = _tasks.pop(name, None)
    if task and not task.done():
        task.cancel()


def _format_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} 秒"
    if seconds < 3600:
        return f"{seconds // 60} 分钟"
    if seconds < 86400:
        return f"{seconds // 3600} 小时"
    return f"{seconds // 86400} 天"
