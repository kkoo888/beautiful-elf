"""Episode Repository — 对话 Episode CRUD + 关联查询"""
from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.memory_episode import MemoryEpisode


class EpisodeRepository:
    """Episode Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(MemoryEpisode)

    # ── CRUD ────────────────────────────────────────────

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[MemoryEpisode]:
        return await self.mapper.find_by_id(db, id)

    async def find_by_conversation(
        self, db: AsyncSession, conversation_id: int,
    ) -> Optional[MemoryEpisode]:
        """按 conversation_id 查找（UNIQUE 索引，去重用）"""
        stmt = select(MemoryEpisode).where(
            MemoryEpisode.conversation_id == conversation_id,
            MemoryEpisode.is_deleted == 0,
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def find_all(
        self, db: AsyncSession, user_id: int = 0,
        offset: int = 0, limit: int = 20,
    ) -> List[MemoryEpisode]:
        """分页列表"""
        return await self.mapper.find_all(
            db, filters={"user_id": user_id},
            offset=offset, limit=limit,
            order_by=MemoryEpisode.started_at.desc(),
        )

    async def count(self, db: AsyncSession, user_id: int = 0) -> int:
        return await self.mapper.count(db, filters={"user_id": user_id})

    async def create(self, db: AsyncSession, data: dict) -> MemoryEpisode:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[MemoryEpisode]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    # ── 关联查询 ────────────────────────────────────────

    async def find_by_entity(
        self, db: AsyncSession, entity_id: int, user_id: int = 0, limit: int = 20,
    ) -> List[MemoryEpisode]:
        """按实体 ID 查找关联 Episode（FIND_IN_SET 精确匹配逗号分隔字符串）"""
        stmt = select(MemoryEpisode).where(
            MemoryEpisode.is_deleted == 0,
            func.find_in_set(str(entity_id), MemoryEpisode.entity_ids) > 0,
        )
        if user_id:
            stmt = stmt.where(MemoryEpisode.user_id == user_id)
        stmt = stmt.order_by(MemoryEpisode.started_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_time_range(
        self, db: AsyncSession, user_id: int,
        start_time: str, end_time: str, limit: int = 20,
    ) -> List[MemoryEpisode]:
        """按时间范围查找 Episode"""
        from datetime import datetime
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        stmt = select(MemoryEpisode).where(
            MemoryEpisode.is_deleted == 0,
            MemoryEpisode.user_id == user_id,
            MemoryEpisode.started_at >= start_dt,
            MemoryEpisode.started_at <= end_dt,
        ).order_by(MemoryEpisode.started_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def append_observation(
        self, db: AsyncSession, episode_id: int, observation_id: int,
    ) -> bool:
        """追加 observation_id 到 Episode 的 observation_ids 字段"""
        episode = await self.find_by_id(db, episode_id)
        if not episode:
            return False
        existing_ids = episode.observation_ids or ""
        id_str = str(observation_id)
        if id_str in existing_ids.split(","):
            return True  # 已存在，幂等
        new_ids = f"{existing_ids},{id_str}" if existing_ids else id_str
        episode.observation_ids = new_ids
        await db.flush()
        return True
