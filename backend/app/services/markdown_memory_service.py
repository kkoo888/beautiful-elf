"""Markdown 记忆文件 Service — 业务编排层

职责:
  - Markdown 记忆 CRUD
  - 与 Qdrant 向量同步
  - daily log 自动创建

遵循规范:
  - 分层架构: service 调用 repository
  - 统一异常: RecordNotFoundError
"""
from typing import List, Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.markdown_memory_repo import MarkdownMemoryRepository
from app.schemas.memory_v2 import MarkdownMemoryCreate, MarkdownMemoryOut, MarkdownMemoryListOut
from app.core.exceptions import RecordNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class MarkdownMemoryService:
    """Markdown 记忆文件业务服务"""

    def __init__(self):
        self.repo = MarkdownMemoryRepository()
        self._memory_manager = None

    def set_memory_manager(self, manager):
        """注入 MemoryManager 实例（应用启动时调用）"""
        self._memory_manager = manager

    # ── CRUD ────────────────────────────────────────────

    async def list_memories(
        self, db: AsyncSession, user_id: int = 0,
        page: int = 1, page_size: int = 20,
        memory_type: Optional[str] = None,
    ) -> Tuple[List[MarkdownMemoryListOut], int]:
        """获取记忆列表"""
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size,
                                          user_id=user_id, memory_type=memory_type)
        total = await self.repo.count(db, user_id=user_id, memory_type=memory_type)
        return [self._to_list_out(i) for i in items], total

    async def get_memory(self, db: AsyncSession, memory_id: int) -> MarkdownMemoryOut:
        """获取记忆详情"""
        item = await self.repo.find_by_id(db, memory_id)
        if not item:
            raise RecordNotFoundError("记忆文件不存在")
        return self._to_out(item)

    async def get_by_title(self, db: AsyncSession, user_id: int, title: str) -> Optional[MarkdownMemoryOut]:
        """按标题查找"""
        item = await self.repo.find_by_title(db, user_id, title)
        if not item:
            return None
        return self._to_out(item)

    async def upsert_memory(
        self, db: AsyncSession, user_id: int, data: MarkdownMemoryCreate
    ) -> MarkdownMemoryOut:
        """创建或更新记忆文件"""
        item = await self.repo.upsert(
            db, user_id=user_id,
            title=data.title, content=data.content,
            memory_type=data.memory_type,
        )
        # 异步同步到 Qdrant
        if self._memory_manager:
            try:
                await self._sync_to_vector(item.id, user_id, data.title, data.content)
            except Exception as e:
                logger.warning(f"[markdown_memory] 向量同步失败: {e}")

        return self._to_out(item)

    async def append_daily_log(
        self, db: AsyncSession, user_id: int, content: str
    ) -> MarkdownMemoryOut:
        """追加到今日 daily log"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        existing = await self.repo.find_by_title(db, user_id, today)

        if existing:
            new_content = existing.content + "\n" + content
            item = await self.repo.upsert(db, user_id, today, new_content, "daily")
        else:
            # 新建 daily log，加日期标题
            header = f"# {today} 每日日志\n\n"
            item = await self.repo.upsert(db, user_id, today, header + content, "daily")

        return self._to_out(item)

    async def get_or_create_longterm(self, db: AsyncSession, user_id: int = 0) -> MarkdownMemoryOut:
        """获取或创建长期记忆文件"""
        existing = await self.repo.find_by_title(db, user_id, "MEMORY")
        if existing:
            return self._to_out(existing)
        # 创建默认长期记忆
        default_content = "# 长期记忆\n\n> 由 Agent 自动提炼和用户手动维护\n\n"
        item = await self.repo.upsert(db, user_id, "MEMORY", default_content, "longterm")
        return self._to_out(item)

    async def update_longterm(
        self, db: AsyncSession, user_id: int, content: str
    ) -> MarkdownMemoryOut:
        """更新长期记忆内容"""
        item = await self.repo.upsert(db, user_id, "MEMORY", content, "longterm")
        return self._to_out(item)

    async def list_daily_logs(
        self, db: AsyncSession, user_id: int = 0, limit: int = 7
    ) -> List[MarkdownMemoryListOut]:
        """获取最近 N 天的 daily log 列表"""
        items = await self.repo.find_all(
            db, offset=0, limit=limit,
            user_id=user_id, memory_type="daily",
        )
        return [self._to_list_out(i) for i in items]

    async def delete_memory(self, db: AsyncSession, memory_id: int) -> bool:
        """软删除记忆"""
        return await self.repo.soft_delete(db, memory_id)

    # ── 向量同步 ────────────────────────────────────────

    async def _sync_to_vector(self, memory_id: int, user_id: int, title: str, content: str):
        """将 Markdown 内容同步到 Qdrant 向量"""
        if not self._memory_manager:
            return
        await self._memory_manager.save_memory(
            user_id=user_id,
            summary=f"[{title}] {content[:500]}",
            tags=[f"markdown:{title}"],
            importance=6,
        )
        await self.repo.mark_synced(None, memory_id)  # 注意: 需要 db session

    # ── 转换 ────────────────────────────────────────────

    @staticmethod
    def _to_out(item) -> MarkdownMemoryOut:
        return MarkdownMemoryOut(
            id=item.id,
            user_id=item.user_id,
            title=item.title,
            content=item.content,
            memory_type=item.memory_type,
            word_count=item.word_count,
            qdrant_synced=item.qdrant_synced,
        )

    @staticmethod
    def _to_list_out(item) -> MarkdownMemoryListOut:
        return MarkdownMemoryListOut(
            id=item.id,
            title=item.title,
            memory_type=item.memory_type,
            word_count=item.word_count,
            created_at=str(item.created_at) if item.created_at else None,
            updated_at=str(item.updated_at) if item.updated_at else None,
        )


# 全局单例
markdown_memory_service = MarkdownMemoryService()
