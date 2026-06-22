"""抖动退避 — 去相关重试延迟（对标 Hermes Agent）

替代固定指数退避，用抖动延迟防止多会话同时重试导致雷群效应。
"""
from __future__ import annotations
import random
import threading
import time

# 进程内单调计数器，确保抖动种子唯一性
_jitter_counter = 0
_jitter_lock = threading.Lock()


def jittered_backoff(
    attempt: int,
    *,
    base_delay: float = 5.0,
    max_delay: float = 120.0,
    jitter_ratio: float = 0.5,
) -> float:
    """计算抖动指数退避延迟

    Args:
        attempt: 1-based 重试次数
        base_delay: 第 1 次重试的基础延迟（秒）
        max_delay: 最大延迟上限（秒）
        jitter_ratio: 抖动范围比例（0.5 = 延迟的 50% 作为随机抖动）

    Returns:
        延迟秒数: min(base * 2^(attempt-1), max_delay) + jitter

    抖动去相关了并发重试，多个会话同时命中同一限流 provider 时
    不会在同一瞬间重试。
    """
    global _jitter_counter
    with _jitter_lock:
        _jitter_counter += 1
        tick = _jitter_counter

    exponent = max(0, attempt - 1)
    if exponent >= 63 or base_delay <= 0:
        delay = max_delay
    else:
        delay = min(base_delay * (2 ** exponent), max_delay)

    # 用时间 + 计数器做种子，即使时钟精度低也能去相关
    seed = (time.time_ns() ^ (tick * 0x9E3779B9)) & 0xFFFFFFFF
    rng = random.Random(seed)
    jitter = rng.uniform(0, jitter_ratio * delay)

    return delay + jitter
