"""Redis Mapper - 封装缓存操作"""
from typing import Optional
import json
import redis.asyncio as aioredis

from app.core.database import get_redis
from app.core.exceptions import StorageError
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisMapper:
    """封装 Redis 缓存操作"""

    def __init__(self):
        self._client = get_redis()

    async def get(self, key: str) -> Optional[str]:
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis GET 失败: {key}, error={e}")
            return None

    async def set(self, key: str, value: str, ttl: int = None) -> None:
        try:
            await self._client.set(key, value, ex=ttl)
        except Exception as e:
            logger.warning(f"Redis SET 失败: {key}, error={e}")

    async def get_json(self, key: str) -> Optional[dict]:
        """获取 JSON 缓存"""
        data = await self.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(self, key: str, value: dict, ttl: int = None) -> None:
        """设置 JSON 缓存"""
        await self.set(key, json.dumps(value, ensure_ascii=False), ttl)

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.warning(f"Redis DELETE 失败: {key}, error={e}")

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self._client.exists(key))
        except Exception as e:
            logger.warning(f"Redis EXISTS 失败: {key}, error={e}")
            return False

    async def publish(self, channel: str, message: str) -> None:
        """发布消息到频道"""
        try:
            await self._client.publish(channel, message)
        except Exception as e:
            logger.warning(f"Redis PUBLISH 失败: {channel}, error={e}")

    async def close(self):
        """关闭连接"""
        await self._client.close()
