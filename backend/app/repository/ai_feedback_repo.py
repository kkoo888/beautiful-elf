"""AI 回答反馈 Repository"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.models import AIFeedback


class AIFeedbackRepository:
    def __init__(self):
        self.mapper = MySQLMapper(AIFeedback)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[AIFeedback]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        feedback_type: Optional[int] = None,
    ) -> List[AIFeedback]:
        filters = {}
        if feedback_type is not None:
            filters["feedback_type"] = feedback_type
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, feedback_type: Optional[int] = None) -> int:
        filters = {}
        if feedback_type is not None:
            filters["feedback_type"] = feedback_type
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> AIFeedback:
        return await self.mapper.create(db, data)

    async def get_stats(self, db: AsyncSession) -> dict:
        """统计反馈数据"""
        from sqlalchemy import select, func

        # 总反馈数
        total_stmt = select(func.count()).select_from(AIFeedback).where(AIFeedback.deleted == 0)
        total_result = await db.execute(total_stmt)
        total = total_result.scalar() or 0

        # 好评数
        like_stmt = select(func.count()).select_from(AIFeedback).where(
            AIFeedback.deleted == 0, AIFeedback.feedback_type == 0
        )
        like_result = await db.execute(like_stmt)
        like_count = like_result.scalar() or 0

        # 好评率
        like_rate = round(like_count / total * 100, 2) if total > 0 else 0.0

        # reason_tags 统计
        tags_stmt = select(AIFeedback.reason_tags).where(
            AIFeedback.deleted == 0, AIFeedback.reason_tags.isnot(None)
        )
        tags_result = await db.execute(tags_stmt)
        all_tags = tags_result.scalars().all()

        tag_counts: dict = {}
        for tags in all_tags:
            if isinstance(tags, list):
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total": total,
            "like_count": like_count,
            "dislike_count": total - like_count,
            "like_rate": like_rate,
            "tag_counts": tag_counts,
        }
