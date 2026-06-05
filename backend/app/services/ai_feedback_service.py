"""AI 回答反馈 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.ai_feedback_repo import AIFeedbackRepository
from app.schemas.ai_feedback import AIFeedbackCreate, AIFeedbackOut
from app.core.exceptions import RecordNotFoundError


class AIFeedbackService:
    def __init__(self):
        self.repo = AIFeedbackRepository()

    async def create_feedback(self, db: AsyncSession, data: AIFeedbackCreate) -> AIFeedbackOut:
        item = await self.repo.create(db, data.model_dump())
        return self._to_out(item)

    async def get_feedback_by_id(self, db: AsyncSession, id: int) -> AIFeedbackOut:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("反馈记录不存在")
        return self._to_out(item)

    async def list_feedbacks(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        feedback_type: Optional[int] = None,
    ) -> Tuple[List[AIFeedbackOut], int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(
            db, offset=offset, limit=page_size, feedback_type=feedback_type,
        )
        total = await self.repo.count(db, feedback_type=feedback_type)
        return [self._to_out(i) for i in items], total

    async def get_feedback_stats(self, db: AsyncSession) -> dict:
        """统计反馈数据"""
        return await self.repo.get_stats(db)

    @staticmethod
    def _to_out(item) -> AIFeedbackOut:
        """ORM → Pydantic 模型"""
        return AIFeedbackOut.model_validate(item)
