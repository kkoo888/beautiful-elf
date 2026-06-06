"""Data Mapper 基类 - 封装 SQLAlchemy 异步操作"""
from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseModel
from app.core.exceptions import StorageError

T = TypeVar("T", bound=BaseModel)


class MySQLMapper(Generic[T]):
    """通用 MySQL Mapper，封装基础 CRUD"""

    def __init__(self, model: Type[T]):
        self.model = model

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[T]:
        """按 ID 查询（排除软删除）"""
        try:
            stmt = select(self.model).where(
                self.model.id == id, self.model.is_deleted == 0
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            raise StorageError(f"查询失败: {e}")

    async def find_all(
        self,
        db: AsyncSession,
        filters: dict = None,
        offset: int = 0,
        limit: int = 20,
        order_by=None,
    ) -> List[T]:
        """分页查询（排除软删除）"""
        try:
            stmt = select(self.model).where(self.model.is_deleted == 0)
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        stmt = stmt.where(getattr(self.model, key) == value)
            if order_by is not None:
                stmt = stmt.order_by(order_by)
            else:
                stmt = stmt.order_by(self.model.id.desc())
            stmt = stmt.offset(offset).limit(limit)
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise StorageError(f"查询列表失败: {e}")

    async def count(self, db: AsyncSession, filters: dict = None) -> int:
        """统计数量（排除软删除）"""
        try:
            stmt = select(func.count()).select_from(self.model).where(
                self.model.is_deleted == 0
            )
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        stmt = stmt.where(getattr(self.model, key) == value)
            result = await db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            raise StorageError(f"统计失败: {e}")

    async def create(self, db: AsyncSession, data: dict) -> T:
        """创建记录"""
        try:
            instance = self.model(**data)
            db.add(instance)
            await db.flush()
            await db.refresh(instance)
            return instance
        except Exception as e:
            raise StorageError(f"创建失败: {e}")

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[T]:
        """更新记录"""
        try:
            stmt = (
                update(self.model)
                .where(self.model.id == id, self.model.is_deleted == 0)
                .values(**data)
            )
            await db.execute(stmt)
            await db.flush()
            return await self.find_by_id(db, id)
        except Exception as e:
            raise StorageError(f"更新失败: {e}")

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        """软删除"""
        try:
            stmt = (
                update(self.model)
                .where(self.model.id == id, self.model.is_deleted == 0)
                .values(is_deleted=1)
            )
            result = await db.execute(stmt)
            await db.flush()
            return result.rowcount > 0
        except Exception as e:
            raise StorageError(f"删除失败: {e}")

    async def bulk_create(self, db: AsyncSession, items: List[dict]) -> None:
        """批量创建"""
        try:
            instances = [self.model(**item) for item in items]
            db.add_all(instances)
            await db.flush()
        except Exception as e:
            raise StorageError(f"批量创建失败: {e}")
