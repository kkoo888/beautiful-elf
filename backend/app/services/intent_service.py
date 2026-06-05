"""意图 Service — 封装意图 CRUD + 向量同步

职责:
  - 意图 CRUD（MySQL 元数据）
  - 创建/更新/删除后自动同步 Qdrant 向量

遵循规范:
  - 分层架构: service 调用 repository
  - 统一异常: RecordNotFoundError, DuplicateEntryError
  - ORM → Pydantic: _to_out 方法
"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.intent_repo import IntentRepository
from app.schemas.intent import IntentCreate, IntentUpdate, IntentOut
from app.core.exceptions import RecordNotFoundError, DuplicateEntryError
from app.core.logging import get_logger

logger = get_logger(__name__)


class IntentService:
    """意图业务服务"""

    def __init__(self):
        self.repo = IntentRepository()
        self._intent_router = None

    @property
    def intent_router(self):
        return self._intent_router

    def set_intent_router(self, router):
        """注入 IntentRouter 实例（应用启动时调用）"""
        self._intent_router = router

    # ── CRUD ─────────────────────────────────────────────

    async def list_intents(
        self, db: AsyncSession, page: int = 1, page_size: int = 50,
        enabled: Optional[int] = None,
    ) -> Tuple[List[IntentOut], int]:
        """获取意图列表"""
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, enabled=enabled)
        total = await self.repo.count(db, enabled=enabled)
        return [self._to_out(i) for i in items], total

    async def get_intent(self, db: AsyncSession, intent_id: int) -> IntentOut:
        """获取意图详情"""
        item = await self.repo.find_by_id(db, intent_id)
        if not item:
            raise RecordNotFoundError("意图不存在")
        return self._to_out(item)

    async def create_intent(self, db: AsyncSession, data: IntentCreate) -> IntentOut:
        """创建意图 + 同步向量"""
        item = await self.repo.create(db, {
            "name": data.name,
            "description": data.description,
            "trigger_texts": data.trigger_texts,
            "target_module": data.target_module,
            "metadata": data.metadata,
            "is_enabled": 1,
        })

        # 同步向量
        await self._sync_single(db, item)

        return self._to_out(await self.repo.find_by_id(db, item.id))

    async def update_intent(self, db: AsyncSession, intent_id: int, data: IntentUpdate) -> IntentOut:
        """更新意图 + 同步向量"""
        item = await self.repo.find_by_id(db, intent_id)
        if not item:
            raise RecordNotFoundError("意图不存在")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_out(item)

        await self.repo.update(db, intent_id, update_data)

        # 同步向量（触发词可能变更）
        updated = await self.repo.find_by_id(db, intent_id)
        await self._sync_single(db, updated)

        return self._to_out(updated)

    async def delete_intent(self, db: AsyncSession, intent_id: int) -> bool:
        """删除意图 + 删除向量"""
        item = await self.repo.find_by_id(db, intent_id)
        if not item:
            raise RecordNotFoundError("意图不存在")

        # 删除 Qdrant 向量
        if self._intent_router and item.qdrant_point_id:
            await self._intent_router.delete_intent(intent_id, item.qdrant_point_id)

        return await self.repo.soft_delete(db, intent_id)

    async def enable_intent(self, db: AsyncSession, intent_id: int) -> IntentOut:
        """启用意图"""
        item = await self.repo.find_by_id(db, intent_id)
        if not item:
            raise RecordNotFoundError("意图不存在")

        await self.repo.set_enabled(db, intent_id, 1)
        updated = await self.repo.find_by_id(db, intent_id)
        await self._sync_single(db, updated)
        return self._to_out(updated)

    async def disable_intent(self, db: AsyncSession, intent_id: int) -> IntentOut:
        """禁用意图"""
        item = await self.repo.find_by_id(db, intent_id)
        if not item:
            raise RecordNotFoundError("意图不存在")

        await self.repo.set_enabled(db, intent_id, 0)
        return self._to_out(await self.repo.find_by_id(db, intent_id))

    # ── 向量同步 ─────────────────────────────────────────

    async def sync_all(self, db: AsyncSession) -> int:
        """全量同步意图向量"""
        if not self._intent_router:
            return 0
        return await self._intent_router.sync_intents(db)

    async def _sync_single(self, db, intent):
        """同步单个意图向量"""
        if not self._intent_router:
            return
        try:
            await self._intent_router.sync_intents(db)
        except Exception as e:
            logger.warning(f"意图向量同步失败（非致命）: {e}")

    @staticmethod
    def _to_out(item) -> IntentOut:
        """ORM → Pydantic"""
        return IntentOut.model_validate(item)


# ── 全局单例 ──────────────────────────────────────────────

intent_service = IntentService()
