"""视频画廊 Repository"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.video_gallery import VideoGallery


class VideoGalleryRepository:
    """视频画廊仓储"""

    def __init__(self):
        self.mapper = MySQLMapper(VideoGallery)

    async def find_by_id(self, db: AsyncSession, video_id: int) -> Optional[VideoGallery]:
        return await self.mapper.find_by_id(db, video_id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        tag: Optional[str] = None, enabled: Optional[int] = None,
    ) -> List[VideoGallery]:
        filters = {}
        if enabled is not None:
            filters["is_enabled"] = enabled
        items = await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)
        if tag:
            items = [i for i in items if tag in (i.tags or "").split(",")]
        return items

    async def count(
        self, db: AsyncSession, tag: Optional[str] = None, enabled: Optional[int] = None,
    ) -> int:
        filters = {}
        if enabled is not None:
            filters["is_enabled"] = enabled
        total = await self.mapper.count(db, filters=filters)
        if tag:
            stmt = select(func.count()).select_from(VideoGallery).where(
                VideoGallery.is_deleted == 0,
                VideoGallery.tags.contains(tag),
            )
            if enabled is not None:
                stmt = stmt.where(VideoGallery.is_enabled == enabled)
            result = await db.execute(stmt)
            return result.scalar() or 0
        return total

    async def find_all_tags(self, db: AsyncSession) -> List[str]:
        """获取所有已使用的标签"""
        stmt = select(VideoGallery.tags).where(
            VideoGallery.is_deleted == 0, VideoGallery.is_enabled == 1,
        )
        result = await db.execute(stmt)
        all_tags = set()
        for row in result.scalars().all():
            if row:
                for t in row.split(","):
                    t = t.strip()
                    if t:
                        all_tags.add(t)
        return sorted(all_tags)

    async def create(self, db: AsyncSession, data: dict) -> VideoGallery:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, video_id: int, data: dict) -> Optional[VideoGallery]:
        return await self.mapper.update(db, video_id, data)

    async def soft_delete(self, db: AsyncSession, video_id: int) -> bool:
        return await self.mapper.soft_delete(db, video_id)
