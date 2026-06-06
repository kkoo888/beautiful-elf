"""意图路由层 — 向量相似度快速匹配意图

架构:
  用户输入 → 闲聊检测（规则快速拦截） → 语义缓存 → 意图向量匹配
  → 命中意图 → 路由到对应模块
  → 未命中 → 进入 Agent 通用对话

设计原则:
  - 意图识别是用户消息进入系统的第一道门
  - 闲聊检测用规则快速拦截，不走 LLM/Embedding，延迟 <1ms
  - 用向量相似度快速匹配，不走 LLM 推理，延迟低
  - 意图定义存 MySQL intent 表，向量存 Qdrant intent_vectors
"""
import re
import uuid
from typing import Optional, List

from app.core.logging import get_logger

logger = get_logger(__name__)

INTENT_COLLECTION = "intent_vectors"
INTENT_SCORE_THRESHOLD = 0.75  # 默认意图相似度阈值
SEMANTIC_CACHE_COLLECTION = "semantic_cache"
SEMANTIC_CACHE_THRESHOLD = 0.92      # [P2] 语义缓存阈值：从 0.95 调整到 0.92（同义改写区间）
SEMANTIC_CACHE_HIGH_CONFIDENCE = 0.95  # 高置信度：直接返回缓存答案

# 按意图类型可配置的阈值映射（覆盖默认值）
INTENT_THRESHOLD_MAP = {
    "exact_match": 0.90,    # 精确匹配场景（如命令触发）
    "fuzzy_match": 0.70,    # 模糊匹配场景（如自然语言）
    "default": INTENT_SCORE_THRESHOLD,
}

# ── 闲聊检测规则（不走 Embedding，<1ms）─────────────────────

# 问候模式
_GREETING_PATTERNS = [
    r"^(hi|hello|hey|yo|嗨|你好|您好|哈喽|嘿|早|早上好|中午好|下午好|晚上好|晚安|good\s*(morning|afternoon|evening|night))[\s!！。.~～]*$",
    r"^(在吗|在不在|有人吗|喂|哎|诶)[\s?？!！。.]*$",
]

# 告别模式
_FAREWELL_PATTERNS = [
    r"^(bye|goodbye|再见|拜拜|拜|回头见|下次见|走了|先走了|88|886|888)[\s!！。.~～]*$",
]

# 感谢模式
_THANKS_PATTERNS = [
    r"^(谢谢|感谢|多谢|thanks|thank\s*you|thx|3q|谢了|太感谢了|辛苦了)[\s!！。.~～]*$",
]

# 无意义输入（过短或纯符号）
_TRIVIAL_PATTERNS = [
    r"^[\s.。!！?？~～…,，]*$",  # 纯标点/空白
    r"^.{0,2}$",                  # 2字符以内
]

# 闲聊回复模板
_GREETING_REPLIES = [
    "你好呀～ 有什么我可以帮你的吗？ 😊",
    "嗨！很高兴见到你，有什么需要帮忙的吗？",
    "你好！请问有什么可以帮到你的？",
]
_FAREWELL_REPLIES = [
    "再见！有需要随时找我～ 👋",
    "拜拜！下次见～",
]
_THANKS_REPLIES = [
    "不客气！有需要随时找我～ 😊",
    "不用谢，能帮到你就好！",
    "随时为你服务～",
]


def _detect_chitchat(message: str) -> Optional[dict]:
    """
    快速闲聊检测（纯规则，不走 Embedding/LLM）。

    Returns:
        命中: {"intent_name": "chitchat", "subtype": "greeting|farewell|thanks", "reply": str}
        未命中: None
    """
    text = message.strip().lower()
    if not text:
        return None

    # 过短/无意义输入
    for p in _TRIVIAL_PATTERNS:
        if re.match(p, text):
            return {"intent_name": "chitchat", "subtype": "trivial", "reply": "你好！请问有什么可以帮到你的？"}

    # 问候
    for p in _GREETING_PATTERNS:
        if re.match(p, text):
            import random
            return {"intent_name": "chitchat", "subtype": "greeting", "reply": random.choice(_GREETING_REPLIES)}

    # 告别
    for p in _FAREWELL_PATTERNS:
        if re.match(p, text):
            import random
            return {"intent_name": "chitchat", "subtype": "farewell", "reply": random.choice(_FAREWELL_REPLIES)}

    # 感谢
    for p in _THANKS_PATTERNS:
        if re.match(p, text):
            import random
            return {"intent_name": "chitchat", "subtype": "thanks", "reply": random.choice(_THANKS_REPLIES)}

    return None


class IntentRouter:
    """意图路由"""

    def __init__(self, qdrant_mapper, embedding_func, score_threshold: Optional[float] = None):
        """
        Args:
            qdrant_mapper: QdrantMapper 实例
            embedding_func: async embedding 函数 (text -> vector)
            score_threshold: 自定义阈值（覆盖默认值）
        """
        self.qdrant = qdrant_mapper
        self.embedding_func = embedding_func
        self._threshold = score_threshold or INTENT_SCORE_THRESHOLD
        self.qdrant.ensure_collection(INTENT_COLLECTION, vector_size=1024)
        self.qdrant.ensure_collection(SEMANTIC_CACHE_COLLECTION, vector_size=1024)

    async def route(self, user_message: str, user_id: int = 0) -> Optional[dict]:
        """
        意图路由：闲聊检测 → 语义缓存 → 意图匹配 → 未命中。

        Args:
            user_message: 用户消息
            user_id: 用户 ID

        Returns:
            命中: {"intent_id": int, "intent_name": str, "score": float, "target_module": str, ...}
            未命中: None
        """
        if not user_message or not user_message.strip():
            return None

        # 0. 闲聊快速检测（规则，<1ms，不走 Embedding）
        chitchat = _detect_chitchat(user_message)
        if chitchat:
            logger.info(f"[intent_router] 闲聊命中: subtype={chitchat['subtype']}")
            return {
                "intent_id": -2,
                "intent_name": "chitchat",
                "score": 1.0,
                "target_module": "chitchat",
                "trigger_texts": [],
                "cached_answer": chitchat["reply"],
            }

        try:
            vector = await self.embedding_func(user_message)
        except Exception as e:
            logger.warning(f"意图路由 Embedding 失败（降级跳过）: {e}")
            return None

        # 1. 语义缓存检查（热门问答直接返回）
        cached = await self._check_semantic_cache(vector)
        if cached:
            return {
                "intent_id": -1,
                "intent_name": "semantic_cache_hit",
                "score": cached["score"],
                "target_module": "cache",
                "trigger_texts": [],
                "cached_answer": cached["answer"],
            }

        # 2. 意图向量检索（使用可配置阈值）
        results = self.qdrant.search(
            collection=INTENT_COLLECTION,
            query_vector=vector,
            limit=1,
            score_threshold=self._threshold,
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

    async def _check_semantic_cache(self, vector: list) -> Optional[dict]:
        """[P2] 分层语义缓存：
          - >= 0.95 高置信度：直接返回缓存答案
          - >= 0.92 中置信度：返回缓存答案（附标记，前端可展示"可能相关"）
        """
        try:
            results = self.qdrant.search(
                collection=SEMANTIC_CACHE_COLLECTION,
                query_vector=vector,
                limit=1,
                score_threshold=SEMANTIC_CACHE_THRESHOLD,
            )
            if not results:
                return None

            score = results[0].score
            if score >= SEMANTIC_CACHE_THRESHOLD:
                confidence = "high" if score >= SEMANTIC_CACHE_HIGH_CONFIDENCE else "medium"
                logger.info(f"[semantic_cache] 命中: score={score:.3f} confidence={confidence}")
                return {
                    "answer": results[0].payload.get("answer", ""),
                    "score": score,
                    "confidence": confidence,
                }
        except Exception as e:
            logger.debug(f"语义缓存检查失败（非致命）: {e}")
        return None

    async def cache_answer(self, question: str, answer: str):
        """缓存问答对到语义缓存"""
        try:
            vector = await self.embedding_func(question)
            import uuid
            self.qdrant.upsert(
                collection=SEMANTIC_CACHE_COLLECTION,
                point_id=str(uuid.uuid4()),
                vector=vector,
                payload={"question": question, "answer": answer},
            )
        except Exception as e:
            logger.warning(f"语义缓存写入失败: {e}")

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
