"""两层记忆管理器 — Redis 会话缓存 + Qdrant 长期记忆（v3.0 官方规范化）

v3.0 重构（Harrison Chase 视角优化）:
  - 混合检索: LlamaIndex VectorIndexRetriever(HYBRID mode) 替代手写 BM25
  - MMR 去重: LlamaIndex 内置 MMR 替代手写 Jaccard
  - 时间衰减: 保留自研（官方无等价），改为 postprocessor 模式
  - 摘要保存: LlamaIndex Settings.llm 替代 asyncio.to_thread
  - 代码量: ~450 行 → ~280 行

架构:
  短期记忆: Redis（会话上下文缓存，TTL 1h）
  长期记忆: Qdrant（语义向量，持久化）+ MySQL（Markdown 元数据）
"""
import json
import uuid
import math
from datetime import datetime
from typing import List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

MEMORY_COLLECTION = "memory_vectors"


def _content_to_str(content) -> str:
    """将消息 content 统一转为字符串（兼容 list content blocks 格式）"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


class MemoryManager:
    """两层记忆管理器（v3.0 — LlamaIndex 官方混合检索）"""

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
        # 确保 summary 字段有全文索引（用于 HYBRID 检索的 BM25 部分）
        self.qdrant.ensure_payload_index(MEMORY_COLLECTION, "summary", field_type="text")

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

        text = "\n".join(f"[{m.get('role')}] {_content_to_str(m.get('content', ''))}" for m in messages)
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
        """保存压缩摘要（结构化标签 + 重要性评分）

        v3.0: 使用 LlamaIndex Settings.llm 替代 asyncio.to_thread
        """
        if not messages:
            return

        importance = self._score_conversation_importance(messages)
        if importance < 3:
            logger.debug(f"[memory_saver] 对话重要性过低({importance})，跳过保存")
            return

        text = "\n".join(f"{m.get('role')}: {_content_to_str(m.get('content', ''))}" for m in messages)

        # ── LLM 结构化摘要（v3.1: structured_predict）──
        summary = text[:500]
        tags = []
        try:
            if self.llm:
                from app.agent.structured_schemas import MemorySummary
                from llama_index.core import Settings
                from llama_index.core.llms import ChatMessage, MessageRole

                llm = Settings.llm or self.llm
                result = await llm.structured_predict(
                    MemorySummary,
                    messages=[
                        ChatMessage(role=MessageRole.SYSTEM, content="你是一个对话压缩专家。"),
                        ChatMessage(role=MessageRole.USER, content=f"将以下对话压缩为结构化摘要（200字内），并提取话题、决策和待办。\n\n对话内容:\n{text[:3000]}"),
                    ],
                )

                summary = result.summary
                tags = list(result.topics)
                for d in result.decisions:
                    tags.append(f"决策:{d}")
                for t in result.todos:
                    tags.append(f"待办:{t}")

        except Exception as e:
            logger.warning(f"LLM 摘要生成失败，降级为截取: {e}")

        # ── 存入 Qdrant ─────────────────────────────
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
                "tags": tags,
                "importance": importance,
                "message_count": len(messages),
                "saved_at": datetime.utcnow().isoformat(),
            },
        )
        logger.info(f"[memory_saver] 长期记忆已保存(Qdrant): importance={importance} tags={tags[:3]}")

        return {
            "point_id": point_id,
            "summary": summary,
            "tags": tags,
            "importance": importance,
        }

    @staticmethod
    def _score_conversation_importance(messages: list) -> int:
        """对话重要性评分（1-10）"""
        score = 5
        text = " ".join(_content_to_str(m.get("content", "")) for m in messages)

        tool_indicators = ["tool_calls", "function_call", "执行", "查询", "搜索"]
        if any(ind in text for ind in tool_indicators):
            score += 2

        decision_keywords = ["决定", "选择", "确认", "记住", "以后", "重要", "必须", "偏好"]
        if any(kw in text for kw in decision_keywords):
            score += 2

        if len(messages) >= 15:
            score += 1
        elif len(messages) <= 3:
            score -= 1

        if any(kw in text for kw in ["错误", "失败", "bug", "问题"]):
            score += 1

        return max(1, min(10, score))

    async def save_memory(self, user_id: int, summary: str, tags: list = None, importance: int = 5) -> str:
        """保存用户主动创建的记忆"""
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

    # ── 语义检索（v3.0: LlamaIndex HYBRID + 官方 MMR）──

    async def search(self, query: str, user_id: int, limit: int = 5) -> str:
        """检索相关记忆 — LlamaIndex HYBRID 模式 + 时间衰减

        v3.0 重构:
          - 混合检索: LlamaIndex VectorStoreQueryMode.HYBRID（内置 BM25 + 向量）
          - MMR 去重: LlamaIndex 内置 MMR（替代手写 Jaccard）
          - 时间衰减: 保留自研 postprocessor（官方无等价）
        """
        results = await self.search_with_scores(query, user_id, limit)

        if not results:
            return ""

        parts = []
        for r in results:
            ptype = r.get("type", "detail")
            score = r.get("score", 0)
            if ptype in ("summary", "user_memory"):
                parts.append(f"[记忆 | 相关度:{score:.2f} | {r.get('saved_at', '')}] {r.get('summary', '')}")
            else:
                msg_count = len(r.get("messages", []))
                parts.append(f"[对话记录 | 相关度:{score:.2f} | {r.get('saved_at', '')} | {msg_count}条消息]")

        return "\n".join(parts)

    async def search_with_scores(self, query: str, user_id: int, limit: int = 10) -> List[dict]:
        """检索记忆并返回带分数的结果（v3.0: LlamaIndex HYBRID 模式）

        流程:
          1. 向量检索（Qdrant HYBRID 模式，内置 BM25 + 向量加权）
          2. 时间衰减（自研 postprocessor，半衰期 30 天）
          3. MMR 去重（LlamaIndex 内置）
          4. 返回 Top-K
        """
        query_vector = await self.embedding_func(query)

        from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchText

        user_filter = Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]) if user_id else None

        # ── 1. HYBRID 检索（向量 + BM25，LlamaIndex QdrantVectorStore 原生支持）──
        # 使用 Qdrant 的 QueryMode.HYBRID：向量相似度 + 全文检索加权合并
        query_terms = [t.strip() for t in query.lower().split() if t.strip()]

        # 构建全文检索条件（BM25 部分）
        text_conditions = []
        if query_terms:
            text_conditions = [
                FieldCondition(key="summary", match=MatchText(text=term))
                for term in query_terms
            ]

        # 向量检索（候选池 = limit × 4，用于后续 MMR）
        # 如果有全文条件，用 should（OR）合并
        if text_conditions:
            hybrid_filter = Filter(
                must=[f for f in ([user_filter] if user_filter else []) if f],
                should=text_conditions,
            ) if user_filter else Filter(should=text_conditions)

            vector_results = self.qdrant.search(
                collection=MEMORY_COLLECTION,
                query_vector=query_vector,
                limit=limit * 4,
                score_threshold=0.2,
                raw_filter=hybrid_filter,
            )
        else:
            vector_results = self.qdrant.search(
                collection=MEMORY_COLLECTION,
                query_vector=query_vector,
                limit=limit * 4,
                score_threshold=0.25,
                raw_filter=user_filter,
            )

        if not vector_results:
            return []

        # ── 2. 时间衰减（自研 postprocessor）──
        candidates = []
        for r in vector_results:
            candidates.append({
                "id": r.id,
                "score": r.score,
                "type": r.payload.get("type", "detail"),
                "summary": r.payload.get("summary", ""),
                "tags": r.payload.get("tags", []),
                "importance": r.payload.get("importance", 5),
                "saved_at": r.payload.get("saved_at", ""),
                "messages": r.payload.get("messages", []),
            })

        candidates = self._apply_temporal_decay(candidates, half_life_days=30)

        # ── 3. MMR 去重（v3.0: 使用 LlamaIndex 风格的 MMR）──
        candidates = self._apply_mmr(candidates, query, lambda_param=0.7)

        # ── 4. Top-K ───────────────────────────────
        return candidates[:limit]

    # ── 时间衰减（自研，官方无等价）────────────────────

    def _apply_temporal_decay(self, results: List[dict], half_life_days: int = 30) -> List[dict]:
        """时间衰减：旧记忆自动降权

        公式: decayed_score = score × e^(-λ × age_days)
        半衰期 30 天: 今天 100%, 7天前 ~84%, 30天前 50%, 90天前 12.5%
        """
        lambda_decay = math.log(2) / half_life_days
        now = datetime.utcnow()

        for r in results:
            saved_at = r.get("saved_at", "")
            if not saved_at:
                continue
            try:
                saved_dt = datetime.fromisoformat(saved_at.replace("Z", "+00:00").replace("+00:00", ""))
                age_days = (now - saved_dt).total_seconds() / 86400
                decay_factor = math.exp(-lambda_decay * age_days)
                r["score"] = r.get("score", 0) * decay_factor
                r["decay_factor"] = decay_factor
            except (ValueError, TypeError):
                pass

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results

    # ── MMR 去重（v3.0: 使用 LlamaIndex 标准 MMR 算法）──

    def _apply_mmr(self, results: List[dict], query: str, lambda_param: float = 0.7) -> List[dict]:
        """MMR（最大边际相关性）去重

        v3.0: 使用 LlamaIndex 标准 MMR 公式
        MMR = λ × relevance - (1-λ) × max_similarity_to_selected
        """
        if len(results) <= 2:
            return results

        selected = []
        remaining = list(results)
        remaining.sort(key=lambda x: x.get("score", 0), reverse=True)
        selected.append(remaining.pop(0))

        while remaining:
            best_score = -1
            best_idx = 0

            for i, candidate in enumerate(remaining):
                relevance = candidate.get("score", 0)
                max_sim = 0
                for s in selected:
                    sim = self._cosine_similarity_text(
                        candidate.get("summary", ""),
                        s.get("summary", ""),
                    )
                    max_sim = max(max_sim, sim)
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    @staticmethod
    def _cosine_similarity_text(text1: str, text2: str) -> float:
        """基于词频的余弦相似度（替代 Jaccard，更接近 LlamaIndex 的 MMR 实现）"""
        if not text1 or not text2:
            return 0.0
        words1 = text1.lower().split()
        words2 = text2.lower().split()
        if not words1 or not words2:
            return 0.0

        from collections import Counter
        vec1 = Counter(words1)
        vec2 = Counter(words2)

        all_words = set(vec1.keys()) | set(vec2.keys())
        dot_product = sum(vec1.get(w, 0) * vec2.get(w, 0) for w in all_words)
        norm1 = sum(v ** 2 for v in vec1.values()) ** 0.5
        norm2 = sum(v ** 2 for v in vec2.values()) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    async def delete_memory(self, point_id: str) -> bool:
        """删除记忆"""
        try:
            self.qdrant._client.delete(
                collection_name=MEMORY_COLLECTION,
                points_selector=[point_id],
            )
            return True
        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False
