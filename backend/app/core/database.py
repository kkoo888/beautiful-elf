"""数据库连接管理 - MySQL"""
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# ==================== MySQL ====================
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
            if session.in_transaction():
                await session.commit()
        except Exception:
            if session.in_transaction():
                await session.rollback()
            raise
        finally:
            await session.close()


async def close_db():
    """关闭数据库引擎"""
    await engine.dispose()
