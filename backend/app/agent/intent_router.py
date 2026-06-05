"""意图路由层 — 向量相似度快速匹配意图

架构:
  用户输入 → Embedding → Qdrant intent_vectors 检索
  → 命中意图 → 路由到对应模块
  → 未命中 → 进入 Agent 通用对话

设计原则:
  - 意图识别是用户消息进入系统的第一道门
  - 用向量相似度快速匹配，不走 LLM 推理，延迟低
  - 意图定义存 MySQL intent 表，向量存 Qdrant intent_vectors
"""
import uuid
from typing import Optional, List

from app.core.logging import get_logger

logger = get_logger(__name__)

INTENT_COLLECTION = "intent_vectors"
INTENT_SCORE_THRESHOLD = 0.75  # 意图相似度阈值（余弦相似度）


class IntentRouter:
    """意图路由"""

    def __init__(self, qdrant_mapper, embedding_func):
        """
        Args:
            qdrant_mapper: QdrantMapper 实例
            embedding_func: async embedding 函数 (text -> vector)
        """
        self.qdrant = qdrant_mapper
        self.embedding_func = embedding_func
        self.qdrant.ensure_collection(INTENT_COLLECTION, vector_size=1024)

    async def route(self, user_message: str, user_id: int = 0) -> Optional[dict]:
        """
        意图路由：用户消息 → 向量检索 → 命中/未命中。

        Args:
            user_message: 用户消息
            user_id: 用户 ID（未使用，预留）

        Returns:
            命中: {"intent_id": int, "intent_name": str, "score": float, "target_module": str, "trigger_texts": list}
            未命中: None
        """
        if not user_message or not user_message.strip():
            return None

        try:
            vector = await self.embedding_func(user_message)
        except Exception as e:
            logger.warning(f"意图路由 Embedding 失败（降级跳过）: {e}")
            return None

        results = self.qdrant.search(
            collection=INTENT_COLLECTION,
            query_vector=vector,
            limit=1,
            score_threshold=INTENT_SCORE_THRESHOLD,
        )

        if not results:
            return None

        top = results[0]
        payload = top.payload

        return {
            "intent_id": payload.get("intent_id", 0),
            "intent_name": payload.get("intent_name", "unknown"),
            "score": top.score,
            "target_module": payload.get("target_module", ""),
            "trigger_texts": payload.get("trigger_texts", []),
        }

    async def sync_intents(self, db) -> int:
        """
        从 MySQL intent 表同步意图向量到 Qdrant。
        意图变更时调用（创建/更新/删除意图后）。

        Args:
            db: 数据库会话

        Returns:
            同步的意图数量
        """
        from app.repository.intent_repo import IntentRepository

        repo = IntentRepository()
        intents = await repo.find_all_enabled(db)

        count = 0
        for intent in intents:
            try:
                # 用触发词拼接生成向量
                trigger_text = " ".join(intent.trigger_texts or [])
                if not trigger_text:
                    continue

                vector = await self.embedding_func(trigger_text)
                point_id = intent.qdrant_point_id or str(uuid.uuid4())

                self.qdrant.upsert(
                    collection=INTENT_COLLECTION,
                    point_id=point_id,
                    vector=vector,
                    payload={
                        "intent_id": intent.id,
                        "intent_name": intent.name,
                        "target_module": intent.target_module,
                        "trigger_texts": intent.trigger_texts or [],
                    },
                )

                # 回写 Qdrant point_id
                if not intent.qdrant_point_id:
                    await repo.set_qdrant_point(db, intent.id, point_id)

                count += 1

            except Exception as e:
                logger.warning(f"同步意图 {intent.id} 失败: {e}")

        logger.info(f"意图向量同步完成: {count}/{len(intents)} 个")
        return count

    async def delete_intent(self, intent_id: int, qdrant_point_id: str) -> bool:
        """删除意图向量"""
        if not qdrant_point_id:
            return True
        try:
            self.qdrant._client.delete(
                collection_name=INTENT_COLLECTION,
                points_selector=[qdrant_point_id],
            )
            return True
        except Exception as e:
            logger.error(f"删除意图向量失败: {e}")
            return False
