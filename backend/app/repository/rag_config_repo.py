"""RAG 配置 Repository — 单例模式，只有一条记录"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rag_config import RagConfig


class RagConfigRepository:

    async def get(self, db: AsyncSession) -> Optional[RagConfig]:
        """获取 RAG 配置（单例，id=1）"""
        result = await db.execute(select(RagConfig).where(RagConfig.id == 1))
        return result.scalar_one_or_none()

    async def create_or_update(self, db: AsyncSession, data: dict) -> RagConfig:
        """创建或更新 RAG 配置（单例模式）"""
        config = await self.get(db)
        if config:
            for key, value in data.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)
        else:
            config = RagConfig(id=1, **data)
            db.add(config)
        await db.flush()
        await db.refresh(config)
        return config
