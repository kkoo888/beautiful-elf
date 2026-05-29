"""数据库连接管理 - MySQL / Redis / Qdrant"""
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
import redis.asyncio as aioredis
from qdrant_client import QdrantClient

from app.core.config import get_settings


# ==================== MySQL ====================
settings = get_settings()

engine = create_async_engine(
    settings.MYSQL_URL,
    pool_size=settings.MYSQL_POOL_SIZE,
    max_overflow=settings.MYSQL_MAX_OVERFLOW,
    pool_timeout=settings.MYSQL_POOL_TIMEOUT,
    pool_recycle=settings.MYSQL_POOL_RECYCLE,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库 session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==================== Redis ====================
redis_pool = aioredis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD or None,
    db=settings.REDIS_DB,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True,
)


def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端"""
    return aioredis.Redis(connection_pool=redis_pool)


# ==================== Qdrant ====================
qdrant_client = QdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
    timeout=30,
)


def get_qdrant() -> QdrantClient:
    """获取 Qdrant 客户端"""
    return qdrant_client
