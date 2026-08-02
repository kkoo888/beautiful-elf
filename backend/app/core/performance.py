"""
性能监控工具 - 提供函数执行时间监控和慢查询检测
"""
import time
import functools
import logging
from typing import Callable, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# 性能指标存储
performance_metrics = {
    "slow_queries": [],
    "slow_functions": [],
    "total_queries": 0,
    "total_time": 0.0
}


def monitor_performance(
    threshold_ms: float = 100.0,
    log_slow: bool = True
):
    """
    性能监控装饰器
    
    使用示例：
    @monitor_performance(threshold_ms=50)
    async def slow_function():
        await asyncio.sleep(0.1)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                # 记录性能指标
                performance_metrics["total_queries"] += 1
                performance_metrics["total_time"] += elapsed_ms
                
                # 检查是否超过阈值
                if elapsed_ms > threshold_ms:
                    warning = {
                        "function": func.__name__,
                        "elapsed_ms": round(elapsed_ms, 2),
                        "threshold_ms": threshold_ms,
                        "args": str(args)[:100],
                        "kwargs": str(kwargs)[:100]
                    }
                    performance_metrics["slow_functions"].append(warning)
                    
                    if log_slow:
                        logger.warning(
                            f"Slow function: {func.__name__} "
                            f"took {elapsed_ms:.2f}ms "
                            f"(threshold: {threshold_ms}ms)"
                        )
        
        return wrapper
    return decorator


@asynccontextmanager
async def measure_time(operation_name: str, threshold_ms: float = 100.0):
    """
    上下文管理器，用于测量代码块执行时间
    
    使用示例：
    async with measure_time("database_query"):
        result = await db.execute(query)
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        performance_metrics["total_queries"] += 1
        performance_metrics["total_time"] += elapsed_ms
        
        if elapsed_ms > threshold_ms:
            warning = {
                "operation": operation_name,
                "elapsed_ms": round(elapsed_ms, 2),
                "threshold_ms": threshold_ms
            }
            performance_metrics["slow_queries"].append(warning)
            
            logger.warning(
                f"Slow operation: {operation_name} "
                f"took {elapsed_ms:.2f}ms "
                f"(threshold: {threshold_ms}ms)"
            )


class PerformanceMonitor:
    """
    性能监控器 - 收集和报告性能指标
    """
    
    def __init__(self):
        self.metrics = performance_metrics
    
    def get_slow_queries(self, limit: int = 10):
        """获取慢查询"""
        return self.metrics["slow_queries"][-limit:]
    
    def get_slow_functions(self, limit: int = 10):
        """获取慢函数"""
        return self.metrics["slow_functions"][-limit:]
    
    def get_average_time(self) -> float:
        """获取平均执行时间"""
        total = self.metrics["total_queries"]
        if total == 0:
            return 0.0
        return self.metrics["total_time"] / total
    
    def get_summary(self) -> dict:
        """获取性能摘要"""
        return {
            "total_queries": self.metrics["total_queries"],
            "total_time_ms": round(self.metrics["total_time"], 2),
            "average_time_ms": round(self.get_average_time(), 2),
            "slow_queries_count": len(self.metrics["slow_queries"]),
            "slow_functions_count": len(self.metrics["slow_functions"])
        }
    
    def reset(self):
        """重置指标"""
        self.metrics["slow_queries"].clear()
        self.metrics["slow_functions"].clear()
        self.metrics["total_queries"] = 0
        self.metrics["total_time"] = 0.0


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()
