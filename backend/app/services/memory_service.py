"""长期记忆 Service — 封装 MemoryManager 的业务编排

职责:
  - 记忆 CRUD（MySQL 元数据 + Qdrant 向量）
  - 语义搜索

遵循规范:
  - 分层架构: service 调用 repository + memory_manager
  - 统一异常: RecordNotFoundError
  - ORM → Pydantic: _to_out 方法
"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.memory_repo import MemoryRepository
from app.schemas.memory import (
    MemoryCreate,
    MemoryOut,
    MemorySearchResult,
    MemorySearchResponse,
)
from app.core.exceptions import RecordNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class MemoryService:
    """长期记忆业务服务"""

    def __init__(self):
        self.repo = MemoryRepository()
        self._memory_manager = None

    @property
    def memory_manager(self):
        return self._memory_manager

    def set_memory_manager(self, manager):
        """注入 MemoryManager 实例（应用启动时调用）"""
        self._memory_manager = manager

    # ── 记忆 CRUD ────────────────────────────────────────

    async def list_memories(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        conversation_id: Optional[int] = None,
    ) -> Tuple[List[MemoryOut], int]:
        """获取记忆列表"""
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, conversation_id=conversation_id)
        total = await self.repo.count(db, conversation_id=conversation_id)
        return [self._to_out(i) for i in items], total

    async def get_memory(self, db: AsyncSession, memory_id: int) -> MemoryOut:
        """获取记忆详情"""
        item = await self.repo.find_by_id(db, memory_id)
        if not item:
            raise RecordNotFoundError("记忆不存在")
        return self._to_out(item)

    async def create_memory(self, db: AsyncSession, data: MemoryCreate, user_id: int = 0) -> MemoryOut:
        """
        创建记忆：保存 MySQL 元数据 + Qdrant 向量。
        """
        # 1. 保存 Qdrant 向量
        qdrant_point_id = None
        if self._memory_manager:
            try:
                qdrant_point_id = await self._memory_manager.save_memory(
                    user_id=user_id,
                    summary=data.summary,
                    tags=data.tags,
                    importance=data.importance,
                )
            except Exception as e:
                logger.warning(f"Qdrant 记忆保存失败（非致命）: {e}")

        # 2. 保存 MySQL 元数据
        item = await self.repo.create(db, {
            "conversation_id": data.conversation_id,
            "summary": data.summary,
            "tags": data.tags,
            "importance": data.importance,
            "qdrant_point_id": qdrant_point_id or "",
        })

        return self._to_out(item)

    async def delete_memory(self, db: AsyncSession, memory_id: int) -> bool:
        """删除记忆：软删除 MySQL + 删除 Qdrant 向量"""
        item = await self.repo.find_by_id(db, memory_id)
        if not item:
            raise RecordNotFoundError("记忆不存在")

        # 删除 Qdrant 向量
        if self._memory_manager and item.qdrant_point_id:
            try:
                await self._memory_manager.delete_memory(item.qdrant_point_id)
            except Exception as e:
                logger.warning(f"Qdrant 记忆删除失败（非致命）: {e}")

        # 软删除 MySQL
        return await self.repo.soft_delete(db, memory_id)

    # ── 语义搜索 ─────────────────────────────────────────

    async def search(
        self, db: AsyncSession, query: str, user_id: int = 0, limit: int = 10,
    ) -> MemorySearchResponse:
        """语义搜索记忆"""
        if not self._memory_manager:
            return MemorySearchResponse(items=[], total=0)

        results = await self._memory_manager.search_with_scores(query, user_id=user_id, limit=limit)

        items = []
        for r in results:
            items.append(MemorySearchResult(
                id=r.get("id", 0),
                summary=r.get("summary", ""),
                score=r.get("score", 0),
                tags=r.get("tags", []),
            ))

        return MemorySearchResponse(items=items, total=len(items))

    @staticmethod
    def _to_out(item) -> MemoryOut:
        """ORM → Pydantic"""
        return MemoryOut.model_validate(item)


# ── 全局单例 ──────────────────────────────────────────────

memory_service = MemoryService()
