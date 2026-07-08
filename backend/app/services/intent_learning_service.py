"""意图学习 Service — 纠正/模式/建议业务逻辑

方案 B + ProactiveAgent 借鉴：
  - accept_suggestion: 创建技能 + 标记模式已解决 + 更新反馈
  - ignore_suggestion: 更新忽略计数 + 连续忽略 3 次自动过滤
  - 用户反馈循环：忽略 → 降低后续建议权重

断点修复：
  - create_correction → 自动更新意图触发词 + 同步 Qdrant
  - analyze → 高频模式自动创建意图
"""
from typing import List, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.intent_learning_repo import (
    IntentCorrectionRepository,
    BehaviorPatternRepository,
    SkillSuggestionRepository,
)
from app.repository.intent_repo import IntentRepository
from app.repository.skill_repo import SkillRepository
from app.schemas.intent_learning import (
    IntentCorrectionOut, IntentCorrectionCreate,
    BehaviorPatternOut,
    SkillSuggestionOut,
)
from app.schemas.skill import SkillOut
from app.core.exceptions import RecordNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

# 连续忽略阈值（超过此次数不再建议同类技能）
IGNORE_THRESHOLD = 3

# 高频模式 → 自动创建意图的阈值
AUTO_INTENT_FREQUENCY = 10


class IntentLearningService:
    """意图学习业务服务"""

    def __init__(self):
        self.correction_repo = IntentCorrectionRepository()
        self.pattern_repo = BehaviorPatternRepository()
        self.suggestion_repo = SkillSuggestionRepository()
        self.intent_repo = IntentRepository()
        self.skill_repo = SkillRepository()

    # ── 纠正历史 ─────────────────────────────────────────

    async def list_corrections(
        self, db: AsyncSession, page: int = 1, page_size: int = 50,
        user_id: int = 0,
    ) -> Tuple[List[IntentCorrectionOut], int]:
        """获取纠正历史列表"""
        offset = (page - 1) * page_size
        items = await self.correction_repo.find_all(db, offset=offset, limit=page_size, user_id=user_id)
        total = await self.correction_repo.count(db, user_id=user_id)
        return [self._to_correction_out(i) for i in items], total

    async def create_correction(
        self, db: AsyncSession, data: IntentCorrectionCreate, user_id: int = 0,
    ) -> IntentCorrectionOut:
        """创建纠正记录 + 自动更新意图触发词

        断点修复：纠正数据回流到意图路由系统
        流程：
          1. 保存纠正记录到 intent_correction 表
          2. 查找正确的意图（按 correct_module 匹配）
          3. 把原始意图文本加入该意图的 trigger_texts
          4. 同步向量到 Qdrant（下次匹配更准确）
        """
        # 1. 保存纠正记录
        item = await self.correction_repo.create(db, {
            "original_intent": data.original_intent,
            "correct_module": data.correct_module,
            "user_id": user_id,
        })

        # 2. 查找正确的意图
        try:
            # 延迟导入：避免循环依赖（intent_repo 依赖 Intent 模型）
            intent = await self.intent_repo.find_by_name(db, data.correct_module)
            if intent:
                # 3. 把原始意图加入触发词（去重）
                trigger_texts = list(intent.trigger_texts or [])
                if data.original_intent not in trigger_texts:
                    trigger_texts.append(data.original_intent)
                    await self.intent_repo.update(db, intent.id, {
                        "trigger_texts": trigger_texts,
                    })
                    logger.info(f"[intent_learning] 纠正回流: '{data.original_intent[:30]}' → 意图 '{intent.name}' 触发词已更新")
            else:
                # 正确模块不存在，创建新意图
                from app.models.intent import Intent
                new_intent = await self.intent_repo.create(db, {
                    "name": data.correct_module,
                    "description": f"从意图纠正自动创建: {data.correct_module}",
                    "trigger_texts": [data.original_intent],
                    "target_module": data.correct_module,
                    "tool_names": None,
                    "is_enabled": 1,
                })
                logger.info(f"[intent_learning] 纠正回流: 创建新意图 '{data.correct_module}' (id={new_intent.id})")
        except Exception as e:
            logger.warning(f"[intent_learning] 纠正回流失败（非致命）: {e}")

        return self._to_correction_out(item)

    # ── 行为模式 ─────────────────────────────────────────

    async def list_patterns(
        self, db: AsyncSession, page: int = 1, page_size: int = 50,
        user_id: int = 0, unsolved_only: bool = False,
    ) -> Tuple[List[BehaviorPatternOut], int]:
        """获取行为模式列表"""
        offset = (page - 1) * page_size
        items = await self.pattern_repo.find_all(
            db, offset=offset, limit=page_size, user_id=user_id, unsolved_only=unsolved_only,
        )
        total = await self.pattern_repo.count(db, user_id=user_id, unsolved_only=unsolved_only)
        return [self._to_pattern_out(i) for i in items], total

    async def create_intent_from_pattern(
        self, db: AsyncSession, pattern_id: int,
    ) -> Optional[dict]:
        """从行为模式创建意图（断点修复：模式 → 意图系统）

        流程：
          1. 查找行为模式
          2. 检查是否已有类似意图
          3. 创建意图 + 同步向量
          4. 标记模式已解决
        """
        pattern = await self.pattern_repo.find_by_id(db, pattern_id)
        if not pattern:
            raise RecordNotFoundError("行为模式不存在")

        # 检查是否已有类似意图（按触发词匹配）
        if pattern.actions:
            for action in pattern.actions:
                existing = await self._find_intent_by_trigger(db, action)
                if existing:
                    logger.info(f"[intent_learning] 模式→意图: 已存在类似意图 '{existing.name}'")
                    await self.pattern_repo.mark_solved(db, pattern_id)
                    return {"intent_id": existing.id, "intent_name": existing.name, "status": "existing"}

        # 创建新意图
        try:
            new_intent = await self.intent_repo.create(db, {
                "name": pattern.description[:50],
                "description": f"从行为模式自动创建: {pattern.description}",
                "trigger_texts": pattern.actions or [],
                "target_module": "auto_pattern",
                "tool_names": None,
                "is_enabled": 1,
            })
            await self.pattern_repo.mark_solved(db, pattern_id)
            logger.info(f"[intent_learning] 模式→意图: 创建新意图 '{new_intent.name}' (id={new_intent.id})")
            return {"intent_id": new_intent.id, "intent_name": new_intent.name, "status": "created"}
        except Exception as e:
            logger.warning(f"[intent_learning] 模式→意图创建失败: {e}")
            return None

    # ── 技能建议 ─────────────────────────────────────────

    async def list_suggestions(
        self, db: AsyncSession, page: int = 1, page_size: int = 50,
        user_id: int = 0, status: Optional[int] = None,
    ) -> Tuple[List[SkillSuggestionOut], int]:
        """获取技能建议列表"""
        offset = (page - 1) * page_size
        items = await self.suggestion_repo.find_all(
            db, offset=offset, limit=page_size, user_id=user_id, status=status,
        )
        total = await self.suggestion_repo.count(db, user_id=user_id, status=status)
        return [self._to_suggestion_out(i) for i in items], total

    async def accept_suggestion(self, db: AsyncSession, suggestion_id: int) -> SkillOut:
        """接受建议 → 自动创建技能 + 标记模式已解决"""
        suggestion = await self.suggestion_repo.find_by_id(db, suggestion_id)
        if not suggestion:
            raise RecordNotFoundError("技能建议不存在")
        if suggestion.status != 0:
            raise RecordNotFoundError("该建议已被处理")

        # 从关联行为模式推导触发词
        trigger_words = []
        if suggestion.pattern_id > 0:
            pattern = await self.pattern_repo.find_by_id(db, suggestion.pattern_id)
            if pattern and pattern.actions:
                trigger_words = pattern.actions
                await self.pattern_repo.mark_solved(db, pattern.id)
                logger.info(f"[intent_learning] 模式 {pattern.id} 已标记为已解决")

        # 检查技能名是否已存在
        existing_skill = await self.skill_repo.find_by_name(db, suggestion.name)
        if existing_skill:
            await self.suggestion_repo.update_status(db, suggestion_id, 1)
            await self.suggestion_repo.update_feedback(db, suggestion_id, "accepted")
            return SkillOut.model_validate(existing_skill)

        # 创建技能
        skill_data = {
            "name": suggestion.name,
            "display_name": suggestion.name,
            "description": suggestion.description,
            "version": "1.0.0",
            "source": "auto-suggestion",
            "trigger_words": trigger_words,
            "dependencies": [],
            "config": {"instructions": suggestion.description},
            "is_enabled": 1,
        }
        skill = await self.skill_repo.create(db, skill_data)

        # 更新建议状态 + 反馈
        await self.suggestion_repo.update_status(db, suggestion_id, 1)
        await self.suggestion_repo.update_feedback(db, suggestion_id, "accepted")

        logger.info(f"[intent_learning] 接受建议 → 创建技能: {suggestion.name} (trigger_words={trigger_words})")
        return SkillOut.model_validate(skill)

    async def ignore_suggestion(self, db: AsyncSession, suggestion_id: int) -> SkillSuggestionOut:
        """忽略建议 + 更新忽略计数"""
        suggestion = await self.suggestion_repo.find_by_id(db, suggestion_id)
        if not suggestion:
            raise RecordNotFoundError("技能建议不存在")
        if suggestion.status != 0:
            raise RecordNotFoundError("该建议已被处理")

        await self.suggestion_repo.update_status(db, suggestion_id, 2)
        await self.suggestion_repo.update_feedback(db, suggestion_id, "ignored", increment_ignore=True)

        updated = await self.suggestion_repo.find_by_id(db, suggestion_id)
        logger.info(f"[intent_learning] 忽略建议: {suggestion.name} (ignore_count={updated.ignore_count})")
        return self._to_suggestion_out(updated)

    # ── 辅助方法 ─────────────────────────────────────────

    async def _find_intent_by_trigger(self, db: AsyncSession, trigger_text: str):
        """按触发词查找意图（JSON_CONTAINS 优化，避免全表加载）"""
        from app.models.intent import Intent
        from sqlalchemy import text
        # 使用 JSON_CONTAINS 在数据库层过滤，避免加载全部意图到内存
        stmt = select(Intent).where(
            Intent.is_deleted == 0,
            Intent.is_enabled == 1,
            text("JSON_CONTAINS(trigger_texts, :trigger)"),
        ).params(trigger=f'"{trigger_text}"')
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── ORM → Pydantic ───────────────────────────────────

    @staticmethod
    def _to_correction_out(item) -> IntentCorrectionOut:
        return IntentCorrectionOut.model_validate(item)

    @staticmethod
    def _to_pattern_out(item) -> BehaviorPatternOut:
        return BehaviorPatternOut.model_validate(item)

    @staticmethod
    def _to_suggestion_out(item) -> SkillSuggestionOut:
        return SkillSuggestionOut.model_validate(item)


# ── 全局单例 ──────────────────────────────────────────────

intent_learning_service = IntentLearningService()
