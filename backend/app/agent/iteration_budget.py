"""迭代预算管理 — 线程安全的 consume/refund 计数器（对标 Hermes Agent）

防止 Agent 无限循环。每个 Agent 实例持有独立预算。
父 Agent 默认 90 次，子 Agent 默认 50 次。
"""
from __future__ import annotations
import threading


class IterationBudget:
    """线程安全的迭代预算计数器

    用法:
        budget = IterationBudget(max_total=90)
        if budget.consume():
            # 执行迭代
        else:
            # 预算耗尽，停止

    execute_code 等程序化调用可以 refund 退还迭代次数。
    """

    def __init__(self, max_total: int = 90):
        self.max_total = max_total
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> bool:
        """消耗一次迭代。返回 True 表示允许继续。"""
        with self._lock:
            if self._used >= self.max_total:
                return False
            self._used += 1
            return True

    def refund(self) -> None:
        """退还一次迭代（如 execute_code 调用）"""
        with self._lock:
            if self._used > 0:
                self._used -= 1

    @property
    def used(self) -> int:
        with self._lock:
            return self._used

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.max_total - self._used)

    def reset(self) -> None:
        """重置预算"""
        with self._lock:
            self._used = 0
