"""意图学习 Repository — 封装纠正/模式/建议 CRUD

ProactiveAgent 借鉴：
  - update_feedback: 更新用户反馈（ignore_count / last_feedback）
  - find_actionable_suggestions: 过滤连续忽略 3 次以上的建议
  - mark_pattern_solved: 标记模式已被技能覆盖
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.intent_learning import IntentCorrection, BehaviorPattern, SkillSuggestion


class IntentCorrectionRepository:
    """意图纠正 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(IntentCorrection)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[IntentCorrection]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 50,
        user_id: int = 0,
    ) -> List[IntentCorrection]:
        filters = {}
        if user_id > 0:
            filters["user_id"] = user_id
        return await self.mapper.find_all(
            db, filters=filters, offset=offset, limit=limit,
            order_by=IntentCorrection.id.desc(),
        )

    async def count(self, db: AsyncSession, user_id: int = 0) -> int:
        filters = {}
        if user_id > 0:
            filters["user_id"] = user_id
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> IntentCorrection:
        return await self.mapper.create(db, data)


class BehaviorPatternRepository:
    """行为模式 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(BehaviorPattern)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[BehaviorPattern]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 50,
        user_id: int = 0, unsolved_only: bool = False,
    ) -> List[BehaviorPattern]:
        filters = {}
        if user_id > 0:
            filters["user_id"] = user_id
        if unsolved_only:
            filters["is_solved"] = 0
        return await self.mapper.find_all(
            db, filters=filters, offset=offset, limit=limit,
            order_by=BehaviorPattern.frequency.desc(),
        )

    async def count(self, db: AsyncSession, user_id: int = 0, unsolved_only: bool = False) -> int:
        filters = {}
        if user_id > 0:
            filters["user_id"] = user_id
        if unsolved_only:
            filters["is_solved"] = 0
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> BehaviorPattern:
        return await self.mapper.create(db, data)

    async def mark_solved(self, db: AsyncSession, id: int) -> bool:
        """标记模式已被技能覆盖"""
        result = await self.mapper.update(db, id, {"is_solved": 1})
        return result is not None


class SkillSuggestionRepository:
    """技能建议 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(SkillSuggestion)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[SkillSuggestion]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 50,
        user_id: int = 0, status: Optional[int] = None,
    ) -> List[SkillSuggestion]:
        filters = {}
        if user_id > 0:
            filters["user_id"] = user_id
        if status is not None:
            filters["status"] = status
        return await self.mapper.find_all(
            db, filters=filters, offset=offset, limit=limit,
            order_by=SkillSuggestion.id.desc(),
        )

    async def count(
        self, db: AsyncSession, user_id: int = 0, status: Optional[int] = None,
    ) -> int:
        filters = {}
        if user_id > 0:
            filters["user_id"] = user_id
        if status is not None:
            filters["status"] = status
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> SkillSuggestion:
        return await self.mapper.create(db, data)

    async def update_status(self, db: AsyncSession, id: int, status: int) -> bool:
        """更新建议状态"""
        result = await self.mapper.update(db, id, {"status": status})
        return result is not None

    async def update_feedback(
        self, db: AsyncSession, id: int, feedback: str, increment_ignore: bool = False,
    ) -> bool:
        """更新用户反馈（ProactiveAgent 借鉴）

        Args:
            feedback: "accepted" 或 "ignored"
            increment_ignore: 是否增加忽略计数
        """
        update_data = {"last_feedback": feedback}
        if increment_ignore:
            # 先查当前值再 +1（MySQLMapper.update 不支持 F() 表达式）
            item = await self.find_by_id(db, id)
            if item:
                update_data["ignore_count"] = item.ignore_count + 1
        result = await self.mapper.update(db, id, update_data)
        return result is not None

    async def find_actionable(self, db: AsyncSession, user_id: int = 0) -> List[SkillSuggestion]:
        """获取可操作的建议（排除连续忽略 3 次以上的）"""
        stmt = select(SkillSuggestion).where(
            SkillSuggestion.is_deleted == 0,
            SkillSuggestion.status == 0,
            SkillSuggestion.ignore_count < 3,
        )
        if user_id > 0:
            stmt = stmt.where(SkillSuggestion.user_id == user_id)
        stmt = stmt.order_by(SkillSuggestion.id.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())
