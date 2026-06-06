"""Redis 客户端 - 独立封装"""
import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()

redis_pool = aioredis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD or None,
    db=settings.REDIS_DB,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True,
)


def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端（FastAPI 依赖注入用）"""
    return aioredis.Redis(connection_pool=redis_pool)


async def close_redis():
    """关闭 Redis 连接池"""
    await redis_pool.disconnect()
