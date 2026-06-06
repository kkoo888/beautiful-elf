"""两层记忆管理器 — Redis 会话缓存 + Qdrant 长期记忆（v2.0 升级版）

v2.0 新增:
  - 混合检索: BM25 关键词 + 向量语义（借鉴 OpenClaw）
  - 时间衰减: 旧记忆自动降权（半衰期 30 天）
  - MMR 去重: 最大边际相关性，避免返回重复记忆
  - Markdown 记忆文件: 支持 daily log 和长期记忆
  - 结构化标签: topics / decisions / todos

架构:
  短期记忆: Redis（会话上下文缓存，TTL 1h）
  长期记忆: Qdrant（语义向量，持久化）+ MySQL（Markdown 元数据）
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
        """保存压缩摘要（结构化标签 + 重要性评分）

        优化:
          - 重要性评分决定是否值得长期保存
          - 结构化标签（topics / decisions / todos）便于后续检索
          - LLM 驱动的智能摘要（非简单截取）
        """
        if not messages:
            return

        # ── 1. 重要性评分 ──────────────────────────────
        importance = self._score_conversation_importance(messages)
        if importance < 3:
            logger.debug(f"[memory_saver] 对话重要性过低({importance})，跳过保存")
            return

        text = "\n".join(f"{m.get('role')}: {m.get('content', '')}" for m in messages)

        # ── 2. LLM 结构化摘要 ─────────────────────────
        summary = text[:500]  # fallback
        tags = []
        try:
            if self.llm:
                import asyncio
                response = await asyncio.to_thread(
                    self.llm.complete,
                    f"""将以下对话压缩为结构化摘要（200字内），并提取标签。

输出格式:
摘要: <压缩后的摘要>
话题: <topic1>, <topic2>, <topic3>
决策: <用户做出的决定，没有则留空>
待办: <需要后续跟进的事项，没有则留空>

对话内容:
{text[:3000]}"""
                )
                result_text = str(response).strip()

                # 解析结构化输出
                lines = result_text.split("\n")
                summary_parts = []
                for line in lines:
                    if line.startswith("摘要:") or line.startswith("摘要："):
                        summary_parts.append(line.split(":", 1)[-1].split("：", 1)[-1].strip())
                    elif line.startswith("话题:") or line.startswith("话题："):
                        topics = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                        tags.extend([t.strip() for t in topics.split(",") if t.strip()])
                    elif line.startswith("决策:") or line.startswith("决策："):
                        decision = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                        if decision:
                            tags.append(f"决策:{decision}")
                    elif line.startswith("待办:") or line.startswith("待办："):
                        todo = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                        if todo:
                            tags.append(f"待办:{todo}")

                if summary_parts:
                    summary = " ".join(summary_parts)
                elif result_text:
                    summary = result_text[:500]

        except Exception as e:
            logger.warning(f"LLM 摘要生成失败，降级为截取: {e}")

        # ── 3. 存入 Qdrant ─────────────────────────────
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
        logger.info(f"[memory_saver] 长期记忆已保存: importance={importance} tags={tags[:3]}")

    @staticmethod
    def _score_conversation_importance(messages: list) -> int:
        """对话重要性评分（1-10）

        高分场景:
          - 包含工具调用（用户在执行实际任务）
          - 用户明确表达需求/偏好/决定
          - 对话轮次多（深度交互）
          - 包含关键词（决定、重要、记住、以后）
        """
        score = 5  # 基础分

        text = " ".join(m.get("content", "") for m in messages)

        # 工具调用加分
        tool_indicators = ["tool_calls", "function_call", "执行", "查询", "搜索"]
        if any(ind in text for ind in tool_indicators):
            score += 2

        # 用户明确表达需求/决定
        decision_keywords = ["决定", "选择", "确认", "记住", "以后", "重要", "必须", "偏好"]
        if any(kw in text for kw in decision_keywords):
            score += 2

        # 对话轮次
        if len(messages) >= 15:
            score += 1
        elif len(messages) <= 3:
            score -= 1

        # 包含错误/失败（值得记录以避免重复）
        if any(kw in text for kw in ["错误", "失败", "bug", "问题"]):
            score += 1

        return max(1, min(10, score))

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
        """检索相关记忆 — 混合搜索（BM25 + 向量）+ 时间衰减 + MMR 去重

        流程:
          1. 向量检索（Qdrant）→ 候选池
          2. BM25 关键词匹配 → 候选池
          3. 加权合并（向量 0.7 + BM25 0.3）
          4. 时间衰减（半衰期 30 天）
          5. MMR 去重（λ=0.7）
          6. 返回 Top-K
        """
        query_vector = await self.embedding_func(query)

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        user_filter = Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]) if user_id else None

        # ── 1. 向量检索（候选池 = limit × 4）──
        vector_results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=query_vector,
            limit=limit * 4,
            score_threshold=0.25,
            filter_payload=user_filter,
        )

        # ── 2. BM25 关键词匹配 ──────────────────────
        bm25_results = self._bm25_search(query, user_id, limit * 4)

        # ── 3. 加权合并 ────────────────────────────
        merged = self._merge_results(
            vector_results=vector_results,
            bm25_results=bm25_results,
            vector_weight=0.7,
            text_weight=0.3,
        )

        # ── 4. 时间衰减 ────────────────────────────
        merged = self._apply_temporal_decay(merged, half_life_days=30)

        # ── 5. MMR 去重 ────────────────────────────
        merged = self._apply_mmr(merged, query, lambda_param=0.7)

        # ── 6. Top-K ───────────────────────────────
        merged = merged[:limit]

        if not merged:
            return ""

        # ── 7. 拼装返回 ────────────────────────────
        parts = []
        for r in merged:
            ptype = r.get("type", "detail")
            score = r.get("score", 0)
            if ptype in ("summary", "user_memory"):
                parts.append(f"[记忆 | 相关度:{score:.2f} | {r.get('saved_at', '')}] {r.get('summary', '')}")
            else:
                msg_count = len(r.get("messages", []))
                parts.append(f"[对话记录 | 相关度:{score:.2f} | {r.get('saved_at', '')} | {msg_count}条消息]")

        return "\n".join(parts)

    async def search_with_scores(self, query: str, user_id: int, limit: int = 10) -> List[dict]:
        """检索记忆并返回带分数的结果（同样使用混合搜索）"""
        query_vector = await self.embedding_func(query)

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        user_filter = Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]) if user_id else None

        vector_results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=query_vector,
            limit=limit * 4,
            score_threshold=0.25,
            filter_payload=user_filter,
        )

        bm25_results = self._bm25_search(query, user_id, limit * 4)
        merged = self._merge_results(vector_results, bm25_results, 0.7, 0.3)
        merged = self._apply_temporal_decay(merged, half_life_days=30)
        merged = self._apply_mmr(merged, query, lambda_param=0.7)

        items = []
        for r in merged[:limit]:
            items.append({
                "id": r.get("id", ""),
                "score": r.get("score", 0),
                "type": r.get("type", ""),
                "summary": r.get("summary", ""),
                "tags": r.get("tags", []),
                "importance": r.get("importance", 5),
                "saved_at": r.get("saved_at", ""),
            })

        return items

    # ── BM25 关键词搜索 ───────────────────────────────

    def _bm25_search(self, query: str, user_id: int, limit: int) -> List[dict]:
        """BM25 关键词匹配（基于 Qdrant payload 中的 summary 文本）

        简化实现：用 Python 端的 TF-IDF 近似 BM25
        生产环境建议用 Elasticsearch 或 SQLite FTS5
        """
        import math
        from collections import Counter

        # 从 Qdrant 获取所有用户记忆（粗暴但有效，后续可换 ES）
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            user_filter = Filter(must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]) if user_id else None

            all_results = self.qdrant.search(
                collection=MEMORY_COLLECTION,
                query_vector=[0.0] * 1024,  # 零向量，不过滤相似度
                limit=500,
                score_threshold=0.0,
                filter_payload=user_filter,
            )
        except Exception:
            return []

        if not all_results:
            return []

        # 简单 BM25 评分
        query_terms = set(query.lower().split())
        if not query_terms:
            return []

        # 计算 IDF
        doc_count = len(all_results)
        doc_freq = Counter()
        for r in all_results:
            text = (r.payload.get("summary", "") or "").lower()
            terms_in_doc = set(text.split())
            for term in query_terms:
                if term in terms_in_doc:
                    doc_freq[term] += 1

        # BM25 参数
        k1 = 1.5
        b = 0.75
        avg_dl = sum(len((r.payload.get("summary", "") or "").split()) for r in all_results) / max(doc_count, 1)

        scored = []
        for r in all_results:
            text = (r.payload.get("summary", "") or "").lower()
            terms = text.split()
            dl = len(terms)
            tf_map = Counter(terms)

            score = 0.0
            for term in query_terms:
                if term not in tf_map:
                    continue
                tf = tf_map[term]
                df = doc_freq.get(term, 0)
                idf = math.log((doc_count - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / max(avg_dl, 1)))
                score += idf * tf_norm

            if score > 0:
                scored.append({
                    "id": r.id,
                    "score": score,
                    "type": r.payload.get("type", "detail"),
                    "summary": r.payload.get("summary", ""),
                    "tags": r.payload.get("tags", []),
                    "importance": r.payload.get("importance", 5),
                    "saved_at": r.payload.get("saved_at", ""),
                    "messages": r.payload.get("messages", []),
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    # ── 结果合并（加权）──────────────────────────────

    def _merge_results(
        self,
        vector_results: list,
        bm25_results: list,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
    ) -> List[dict]:
        """加权合并向量和 BM25 结果"""
        # 归一化分数
        def normalize(results: list, score_key: str = "score") -> dict:
            if not results:
                return {}
            max_score = max(r.get(score_key, 0) for r in results) or 1
            return {
                r.id if hasattr(r, "id") else r.get("id", ""): {
                    "id": r.id if hasattr(r, "id") else r.get("id", ""),
                    "score": (r.score if hasattr(r, "score") else r.get("score", 0)) / max_score,
                    "type": (r.payload if hasattr(r, "payload") else r).get("type", "detail") if hasattr(r, "payload") else r.get("type", "detail"),
                    "summary": (r.payload if hasattr(r, "payload") else r).get("summary", "") if hasattr(r, "payload") else r.get("summary", ""),
                    "tags": (r.payload if hasattr(r, "payload") else r).get("tags", []) if hasattr(r, "payload") else r.get("tags", []),
                    "importance": (r.payload if hasattr(r, "payload") else r).get("importance", 5) if hasattr(r, "payload") else r.get("importance", 5),
                    "saved_at": (r.payload if hasattr(r, "payload") else r).get("saved_at", "") if hasattr(r, "payload") else r.get("saved_at", ""),
                    "messages": (r.payload if hasattr(r, "payload") else r).get("messages", []) if hasattr(r, "payload") else r.get("messages", []),
                }
                for r in results
            }

        vec_map = normalize(vector_results)
        bm25_map = normalize(bm25_results)

        # 合并
        all_ids = set(vec_map.keys()) | set(bm25_map.keys())
        merged = []
        for doc_id in all_ids:
            vec_score = vec_map.get(doc_id, {}).get("score", 0) * vector_weight
            bm25_score = bm25_map.get(doc_id, {}).get("score", 0) * text_weight
            combined_score = vec_score + bm25_score

            doc = vec_map.get(doc_id) or bm25_map.get(doc_id)
            doc["score"] = combined_score
            merged.append(doc)

        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged

    # ── 时间衰减 ──────────────────────────────────────

    def _apply_temporal_decay(self, results: List[dict], half_life_days: int = 30) -> List[dict]:
        """时间衰减：旧记忆自动降权

        公式: decayed_score = score × e^(-λ × age_days)
        其中 λ = ln(2) / half_life_days

        半衰期 30 天:
          - 今天: 100%
          - 7 天前: ~84%
          - 30 天前: 50%
          - 90 天前: 12.5%
        """
        import math
        from datetime import datetime

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

    # ── MMR 去重 ──────────────────────────────────────

    def _apply_mmr(self, results: List[dict], query: str, lambda_param: float = 0.7) -> List[dict]:
        """MMR（最大边际相关性）去重

        平衡相关性和多样性:
          MMR = λ × relevance - (1-λ) × max_similarity_to_selected

        lambda_param:
          - 1.0 = 纯相关性（不去重）
          - 0.0 = 最大多样性
          - 0.7 = 默认（轻微去重）
        """
        if len(results) <= 2:
            return results

        selected = []
        remaining = list(results)

        # 选第一个（分数最高的）
        remaining.sort(key=lambda x: x.get("score", 0), reverse=True)
        selected.append(remaining.pop(0))

        while remaining:
            best_score = -1
            best_idx = 0

            for i, candidate in enumerate(remaining):
                relevance = candidate.get("score", 0)

                # 计算与已选结果的最大相似度
                max_sim = 0
                for s in selected:
                    sim = self._jaccard_similarity(
                        candidate.get("summary", ""),
                        s.get("summary", ""),
                    )
                    max_sim = max(max_sim, sim)

                # MMR 分数
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    @staticmethod
    def _jaccard_similarity(text1: str, text2: str) -> float:
        """Jaccard 文本相似度"""
        if not text1 or not text2:
            return 0.0
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

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
