"""
缓存装饰器 - 提供声明式缓存
支持Redis和内存缓存
"""
import functools
import hashlib
import json
import logging
from typing import Optional, Callable, Any
from datetime import timedelta

logger = logging.getLogger(__name__)


def cached(
    ttl: int = 300,
    key_prefix: str = "",
    cache_type: str = "memory"
):
    """
    缓存装饰器
    
    使用示例：
    @cached(ttl=60, key_prefix="user")
    async def get_user(user_id: int):
        return await db.get_user(user_id)
    """
    def decorator(func: Callable):
        # 内存缓存
        memory_cache = {}
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)
            
            # 检查缓存
            if cache_type == "memory":
                if cache_key in memory_cache:
                    value, expiry = memory_cache[cache_key]
                    if expiry is None or expiry > _now():
                        logger.debug(f"Cache hit: {cache_key}")
                        return value
                    else:
                        del memory_cache[cache_key]
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 存储缓存
            if cache_type == "memory":
                expiry = _now() + timedelta(seconds=ttl) if ttl > 0 else None
                memory_cache[cache_key] = (result, expiry)
                logger.debug(f"Cache set: {cache_key}")
            
            return result
        
        # 添加缓存管理方法
        wrapper.cache_clear = lambda: memory_cache.clear()
        wrapper.cache_info = lambda: {
            "size": len(memory_cache),
            "keys": list(memory_cache.keys())
        }
        
        return wrapper
    return decorator


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict, prefix: str) -> str:
    """生成缓存键"""
    # 排除第一个参数（通常是self）
    key_parts = [prefix or func.__name__]
    
    # 添加位置参数
    for arg in args[1:]:  # 跳过self
        key_parts.append(str(arg))
    
    # 添加关键字参数
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    # 生成哈希
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def _now():
    """获取当前时间"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


class CacheManager:
    """
    缓存管理器 - 统一管理多种缓存
    """
    
    def __init__(self):
        self._memory_cache = {}
        self._redis_client = None
    
    def set_redis(self, redis_client):
        """设置Redis客户端"""
        self._redis_client = redis_client
    
    async def get(self, key: str, cache_type: str = "memory") -> Optional[Any]:
        """获取缓存"""
        if cache_type == "memory":
            if key in self._memory_cache:
                value, expiry = self._memory_cache[key]
                if expiry is None or expiry > _now():
                    return value
                else:
                    del self._memory_cache[key]
        elif cache_type == "redis" and self._redis_client:
            value = await self._redis_client.get(key)
            if value:
                return json.loads(value)
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        cache_type: str = "memory"
    ):
        """设置缓存"""
        if cache_type == "memory":
            expiry = _now() + timedelta(seconds=ttl) if ttl > 0 else None
            self._memory_cache[key] = (value, expiry)
        elif cache_type == "redis" and self._redis_client:
            await self._redis_client.setex(key, ttl, json.dumps(value))
    
    async def delete(self, key: str, cache_type: str = "memory"):
        """删除缓存"""
        if cache_type == "memory":
            self._memory_cache.pop(key, None)
        elif cache_type == "redis" and self._redis_client:
            await self._redis_client.delete(key)
    
    async def clear(self, cache_type: str = "memory"):
        """清空缓存"""
        if cache_type == "memory":
            self._memory_cache.clear()
        elif cache_type == "redis" and self._redis_client:
            await self._redis_client.flushdb()


# 全局缓存管理器实例
cache_manager = CacheManager()
