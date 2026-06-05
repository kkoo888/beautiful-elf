"""两层记忆管理器 — Redis 会话缓存 + Qdrant 长期记忆

架构:
  短期记忆: Redis（会话上下文缓存，TTL 1h）
  长期记忆: Qdrant（语义向量，持久化）

职责:
  - 会话缓存读写（Redis）
  - 长期记忆存入 / 检索（Qdrant）
  - 摘要压缩（LLM 驱动）

注意:
  - 本模块是 Agent 引擎的子系统
  - 不含路由细节，由 memory_service 调用
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

MEMORY_COLLECTION = "memory_vectors"


class MemoryManager:
    """两层记忆管理器"""

    def __init__(self, qdrant_mapper, embedding_func, llm_client=None):
        """
        Args:
            qdrant_mapper: QdrantMapper 实例
            embedding_func: async embedding 函数 (text -> vector)
            llm_client: LlamaIndex LLM 实例（用于摘要压缩，可选）
        """
        self.qdrant = qdrant_mapper
        self.embedding_func = embedding_func
        self.llm = llm_client
        self.qdrant.ensure_collection(MEMORY_COLLECTION, vector_size=1024)

    # ── Redis 会话缓存 ──────────────────────────────────

    async def get_session_cache(self, conversation_id: int) -> dict:
        """获取会话缓存"""
        from app.core.redis_client import get_redis
        redis = get_redis()
        data = await redis.get(f"memory:session:{conversation_id}")
        return json.loads(data) if data else {"messages": [], "last_active": None}

    async def update_session_cache(self, conversation_id: int, messages: list):
        """更新会话缓存（保留最近 50 条消息）"""
        from app.core.redis_client import get_redis
        redis = get_redis()
        await redis.set(
            f"memory:session:{conversation_id}",
            json.dumps({
                "messages": messages[-50:],
                "last_active": datetime.utcnow().isoformat(),
            }, ensure_ascii=False),
            ex=3600,  # TTL 1 小时
        )

    # ── 长期记忆存入 Qdrant ─────────────────────────────

    async def save_detail(self, conversation_id: int, user_id: int, messages: list):
        """保存详细对话日志（每小时 Celery 触发）"""
        if not messages:
            return

        text = "\n".join(f"[{m.get('role')}] {m.get('content', '')}" for m in messages)
        vector = await self.embedding_func(text[:2000])
        point_id = str(uuid.uuid4())

        self.qdrant.upsert(
            collection=MEMORY_COLLECTION,
            point_id=point_id,
            vector=vector,
            payload={
                "type": "detail",
                "conversation_id": conversation_id,
                "user_id": user_id,
                "messages": messages,
                "saved_at": datetime.utcnow().isoformat(),
            },
        )

    async def save_summary(self, conversation_id: int, user_id: int, messages: list):
        """保存压缩摘要（30 分钟无互动时触发）"""
        if not messages:
            return

        text = "\n".join(f"{m.get('role')}: {m.get('content', '')}" for m in messages)

        # LLM 压缩
        summary = text[:500]  # fallback
        if self.llm:
            try:
                import asyncio
                response = await asyncio.to_thread(
                    self.llm.complete,
                    f"将以下对话压缩为结构化摘要（200字内），保留：用户核心需求、关键话题、待办事项。\n\n{text[:3000]}"
                )
                summary = str(response).strip() or summary
            except Exception as e:
                logger.warning(f"LLM 摘要生成失败，降级为截取: {e}")

        vector = await self.embedding_func(summary)
        point_id = str(uuid.uuid4())

        self.qdrant.upsert(
            collection=MEMORY_COLLECTION,
            point_id=point_id,
            vector=vector,
            payload={
                "type": "summary",
                "conversation_id": conversation_id,
                "user_id": user_id,
                "summary": summary,
                "saved_at": datetime.utcnow().isoformat(),
            },
        )

    async def save_memory(self, user_id: int, summary: str, tags: list = None, importance: int = 5) -> str:
        """
        保存用户主动创建的记忆。

        Args:
            user_id: 用户 ID
            summary: 记忆摘要
            tags: 标签列表
            importance: 重要度 (1-10)

        Returns:
            Qdrant point_id
        """
        vector = await self.embedding_func(summary)
        point_id = str(uuid.uuid4())

        self.qdrant.upsert(
            collection=MEMORY_COLLECTION,
            point_id=point_id,
            vector=vector,
            payload={
                "type": "user_memory",
                "user_id": user_id,
                "summary": summary,
                "tags": tags or [],
                "importance": importance,
                "saved_at": datetime.utcnow().isoformat(),
            },
        )

        return point_id

    # ── 语义检索 ────────────────────────────────────────

    async def search(self, query: str, user_id: int, limit: int = 5) -> str:
        """检索相关记忆（返回拼装文本）"""
        query_vector = await self.embedding_func(query)

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            score_threshold=0.35,
            filter_payload=Filter(must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]) if user_id else None,
        )

        if not results:
            return ""

        parts = []
        for r in results:
            ptype = r.payload.get("type", "detail")
            if ptype == "summary" or ptype == "user_memory":
                parts.append(f"[记忆 | {r.payload.get('saved_at', '')}] {r.payload.get('summary', '')}")
            else:
                msg_count = len(r.payload.get("messages", []))
                parts.append(f"[对话记录 | {r.payload.get('saved_at', '')} | {msg_count}条消息]")

        return "\n".join(parts)

    async def search_with_scores(self, query: str, user_id: int, limit: int = 10) -> List[dict]:
        """检索记忆并返回带分数的结果"""
        query_vector = await self.embedding_func(query)

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            score_threshold=0.35,
            filter_payload=Filter(must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]) if user_id else None,
        )

        items = []
        for r in results:
            items.append({
                "id": r.id,
                "score": r.score,
                "type": r.payload.get("type", ""),
                "summary": r.payload.get("summary", ""),
                "tags": r.payload.get("tags", []),
                "importance": r.payload.get("importance", 5),
                "saved_at": r.payload.get("saved_at", ""),
            })

        return items

    async def delete_memory(self, point_id: str) -> bool:
        """删除记忆"""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            self.qdrant._client.delete(
                collection_name=MEMORY_COLLECTION,
                points_selector=[point_id],
            )
            return True
        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False
