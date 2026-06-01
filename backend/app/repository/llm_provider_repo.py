"""大模型供应商 Repository"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.llm_provider import LLMProvider


class LLMProviderRepository:
    """大模型供应商数据访问层"""

    def __init__(self):
        self.mapper = MySQLMapper(LLMProvider)

    async def find_by_id(self, db: AsyncSession, provider_id: int) -> Optional[LLMProvider]:
        """按 ID 查询"""
        return await self.mapper.find_by_id(db, provider_id)

    async def find_all(self, db: AsyncSession, offset: int = 0, limit: int = 100) -> List[LLMProvider]:
        """查询全部供应商"""
        return await self.mapper.find_all(db, offset=offset, limit=limit)

    async def count(self, db: AsyncSession) -> int:
        """统计数量"""
        return await self.mapper.count(db)

    async def find_enabled(self, db: AsyncSession) -> List[LLMProvider]:
        """获取所有启用的供应商"""
        return await self.mapper.find_all(
            db, filters={"enabled": 1}, offset=0, limit=100
        )

    async def find_by_type(self, db: AsyncSession, provider_type: str) -> Optional[LLMProvider]:
        """按类型查找供应商"""
        stmt = select(LLMProvider).where(
            LLMProvider.is_deleted == 0,
            LLMProvider.provider_type == provider_type,
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_default(self, db: AsyncSession) -> Optional[LLMProvider]:
        """获取默认供应商"""
        stmt = select(LLMProvider).where(
            LLMProvider.is_deleted == 0,
            LLMProvider.is_default == 1,
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> LLMProvider:
        """创建供应商"""
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, provider_id: int, data: dict) -> Optional[LLMProvider]:
        """更新供应商"""
        return await self.mapper.update(db, provider_id, data)

    async def soft_delete(self, db: AsyncSession, provider_id: int) -> bool:
        """软删除供应商"""
        return await self.mapper.soft_delete(db, provider_id)

    async def clear_default(self, db: AsyncSession) -> None:
        """清除所有默认标记"""
        providers = await self.find_enabled(db)
        for p in providers:
            if p.is_default == 1:
                await self.mapper.update(db, p.id, {"is_default": 0})
