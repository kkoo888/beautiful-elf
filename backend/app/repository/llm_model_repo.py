"""大模型 Model Repository — 独立管理模型配置"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.llm_model import LLMModel


class LLMModelRepository:
    """大模型数据访问层"""

    def __init__(self):
        self.mapper = MySQLMapper(LLMModel)

    async def find_by_id(self, db: AsyncSession, model_id: int) -> Optional[LLMModel]:
        """按 ID 查询"""
        return await self.mapper.find_by_id(db, model_id)

    async def find_by_provider(self, db: AsyncSession, provider_id: int) -> List[LLMModel]:
        """获取供应商下所有模型"""
        stmt = (
            select(LLMModel)
            .where(LLMModel.provider_id == provider_id, LLMModel.is_deleted == 0)
            .order_by(LLMModel.sort_order, LLMModel.id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_enabled_by_provider(self, db: AsyncSession, provider_id: int) -> List[LLMModel]:
        """获取供应商下所有启用的模型"""
        stmt = (
            select(LLMModel)
            .where(
                LLMModel.provider_id == provider_id,
                LLMModel.is_enabled == 1,
                LLMModel.is_deleted == 0,
            )
            .order_by(LLMModel.sort_order, LLMModel.id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_provider_and_name(
        self, db: AsyncSession, provider_id: int, model_name: str
    ) -> Optional[LLMModel]:
        """按供应商+模型名查找"""
        stmt = select(LLMModel).where(
            LLMModel.provider_id == provider_id,
            LLMModel.model_name == model_name,
            LLMModel.is_deleted == 0,
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> LLMModel:
        """创建模型"""
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, model_id: int, data: dict) -> Optional[LLMModel]:
        """更新模型"""
        return await self.mapper.update(db, model_id, data)

    async def soft_delete(self, db: AsyncSession, model_id: int) -> bool:
        """软删除模型"""
        return await self.mapper.soft_delete(db, model_id)

    async def delete_by_provider(self, db: AsyncSession, provider_id: int) -> int:
        """删除供应商下所有模型（供应商被删除时联动）"""
        models = await self.find_by_provider(db, provider_id)
        count = 0
        for m in models:
            if await self.mapper.soft_delete(db, m.id):
                count += 1
        return count

    async def batch_create(self, db: AsyncSession, provider_id: int, models: list[dict]) -> List[LLMModel]:
        """批量创建模型"""
        created = []
        for i, m in enumerate(models):
            m["provider_id"] = provider_id
            if "sort_order" not in m:
                m["sort_order"] = i
            obj = await self.mapper.create(db, m)
            created.append(obj)
        return created

    async def sync_models(self, db: AsyncSession, provider_id: int, models: list[dict]) -> List[LLMModel]:
        """同步模型列表：新增、更新、软删除差异模型"""
        existing = await self.find_by_provider(db, provider_id)
        existing_map = {m.model_name: m for m in existing}
        incoming_names = {m["model_name"] for m in models}

        # 软删除不再存在的模型
        for name, obj in existing_map.items():
            if name not in incoming_names:
                await self.mapper.soft_delete(db, obj.id)

        # 新增或更新
        result = []
        for i, m in enumerate(models):
            m["provider_id"] = provider_id
            m.setdefault("sort_order", i)
            if m["model_name"] in existing_map:
                obj = await self.mapper.update(db, existing_map[m["model_name"]].id, m)
            else:
                obj = await self.mapper.create(db, m)
            if obj:
                result.append(obj)
        return result
