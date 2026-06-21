"""两层记忆管理器 — Redis 会话缓存 + Qdrant 长期记忆（v5.1 实体图增强版）

v5.1 进化（实体图检索通道）:
  - Channel 5: 实体图遍历 — 从 query 提取实体名 → 匹配 MemoryEntity
    → 通过 MemoryEntityRelation 扩展 1 跳邻居 → Qdrant 全文召回

v5.0 进化（Cross-Encoder Rerank + 认知衰减 + 经历 + 冲突仲裁）:
  - Cross-Encoder Rerank: ONNX cross-encoder pair-wise 精排（管线: RRF → Rerank → Decay → MMR）
  - 认知衰减: ACT-R 激活度模型 + dormant 过滤 + 动态半衰期
  - 经历: 对话级分组 + bi-temporal + 实体关联
  - 访问记录: fire-and-forget 更新 access_count + activation

v4.0 保留:
  - 4 路并行检索: 语义 + BM25 + 标签图遍历 + 时间范围
  - RRF 融合: Reciprocal Rank Fusion 合并多路结果
  - Token 预算: 自适应上下文填充
  - 网络分类: world/experience/opinion/observation

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

    def __init__(self, qdrant_mapper, embedding_func, llm_client=None, reranker=None):
        """
        Args:
            qdrant_mapper: QdrantMapper 实例
            embedding_func: async embedding 函数 (text -> vector)
            llm_client: LlamaIndex LLM 实例（用于摘要压缩，可选）
            reranker: OnnxRerankerService 实例（可选，None 时降级为 embedding cosine）
        """
        self.qdrant = qdrant_mapper
        self.embedding_func = embedding_func
        self.llm = llm_client
        self.reranker = reranker
        self.qdrant.ensure_collection(MEMORY_COLLECTION, vector_size=1024)
        # 确保 summary 字段有全文索引（用于 HYBRID 检索的 BM25 部分）
        self.qdrant.ensure_payload_index(MEMORY_COLLECTION, "summary", field_type="text")
        # v5.0: 确保 decay_status 和 activation 有 keyword/float 索引
        self.qdrant.ensure_payload_index(MEMORY_COLLECTION, "decay_status", field_type="keyword")
        self.qdrant.ensure_payload_index(MEMORY_COLLECTION, "activation", field_type="float")

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

    async def save_summary(self, conversation_id: int, user_id: int, messages: list):
        """保存压缩摘要（结构化标签 + 重要性评分 + 网络分类）

        v4.0: 新增 network 分类（借鉴 Hindsight 4 网络）
        v3.0: 使用 LlamaIndex Settings.llm 替代 asyncio.to_thread
        注意: 直接执行 LLM + embedding，会阻塞调用方。
              在请求响应流程中建议使用 enqueue_summary() 异步化。
        """
        return await self._process_summary({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "messages": messages,
        })

    async def enqueue_summary(self, conversation_id: int, user_id: int, messages: list):
        """异步入队压缩摘要（非阻塞）

        v5.1: 将任务推入 Redis list，由 Celery 异步消费。
        调用方无需等待 LLM + embedding 完成。

        Returns:
            True if enqueued, False if skipped (importance too low)
        """
        if not messages:
            return False

        importance = self._score_conversation_importance(messages)
        if importance < 3:
            logger.debug(f"[memory_saver] 对话重要性过低({importance})，跳过入队")
            return False

        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            await redis.rpush(
                "memory:summary_queue",
                json.dumps({
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "messages": messages,
                    "enqueued_at": datetime.utcnow().isoformat(),
                }, ensure_ascii=False),
            )
            logger.debug(f"[memory_saver] 摘要已入队: conv={conversation_id}")
            return True
        except Exception as e:
            logger.warning(f"[memory_saver] 入队失败，降级为同步: {e}")
            # 降级为同步
            return await self.save_summary(conversation_id, user_id, messages)

    async def _process_summary(self, data: dict):
        """处理单条摘要任务（LLM 结构化 + embedding + Qdrant 存储）

        由 save_summary() 或 Celery process_summary_queue 调用。
        """
        conversation_id = data["conversation_id"]
        user_id = data["user_id"]
        messages = data["messages"]

        if not messages:
            return None

        importance = self._score_conversation_importance(messages)
        if importance < 3:
            logger.debug(f"[memory_saver] 对话重要性过低({importance})，跳过保存")
            return None

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

        # ── P1-5: 网络分类（借鉴 Hindsight 4 网络）──
        network = self._classify_network(summary, tags)

        # ── v5.1 合并去重检查（写入前检查相似度 >0.85）──
        consolidation_result = await self._check_consolidation(
            summary=summary,
            user_id=user_id,
            tags=tags,
            importance=importance,
            network=network,
            conversation_id=conversation_id,
            message_count=len(messages),
        )
        if consolidation_result:
            # DELETE 决策: 需要写入新记忆后删除旧的
            pending_delete = consolidation_result.pop("_pending_delete_ids", None)
            if consolidation_result.get("_write_new"):
                consolidation_result.pop("_write_new", None)
                # 继续写入新记忆，然后删除旧的
            else:
                return consolidation_result

        # ── 存入 Qdrant（无相似记忆 / DELETE 后写入新的）──
        vector = await self.embedding_func(summary)
        point_id = str(uuid.uuid4())

        self.qdrant.upsert(
            collection=MEMORY_COLLECTION,
            point_id=point_id,
            vector=vector,
            payload={
                "type": "summary",
                "network": network,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "summary": summary,
                "tags": tags,
                "importance": importance,
                "activation": 1.0,
                "decay_status": "active",
                "message_count": len(messages),
                "saved_at": datetime.utcnow().isoformat(),
                "evidence_count": 1,
                "confidence": 1.0,
            },
        )
        logger.info(f"[memory_saver] 长期记忆已保存(Qdrant): importance={importance} tags={tags[:3]}")

        # v5.1 fix: DELETE 决策写入新记忆成功后，删除旧的（先写后删，避免数据丢失）
        if pending_delete:
            for old_id in pending_delete:
                try:
                    self.qdrant._client.delete(
                        collection_name=MEMORY_COLLECTION,
                        points_selector=[old_id],
                    )
                    logger.info(f"[consolidation] DELETE 完成: 旧记忆 {old_id} 已删除")
                except Exception:
                    pass  # 新的已写入成功，旧的可等下次 sweep 清理

        return {
            "point_id": point_id,
            "summary": summary,
            "tags": tags,
            "importance": importance,
        }

    @staticmethod
    @staticmethod
    def _score_conversation_importance(messages: list) -> int:
        """对话重要性评分（关键词启发式，快速预筛）

        用于 enqueue_summary 的快速判断，避免低价值对话入队。
        精确评分由 LLM 完成（见 _llm_score_importance）。
        """
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

    @staticmethod
    async def _llm_score_importance(messages: list, llm_client=None) -> int:
        """LLM 精确评分（1-10）

        由 LLM 综合判断对话重要性，比关键词启发式更准确。
        用于手动重新评分和 process_summary_queue 的精确判断。

        Args:
            messages: 对话消息列表
            llm_client: LLM 实例（可选，不可用时降级为关键词）

        Returns:
            importance 1-10
        """
        if not llm_client:
            return MemoryManager._score_conversation_importance(messages)

        try:
            from llama_index.core import Settings
            from llama_index.core.llms import ChatMessage, MessageRole

            text = "\n".join(
                f"{m.get('role', 'unknown')}: {_content_to_str(m.get('content', ''))}"
                for m in messages[-20:]  # 最多取 20 条
            )

            llm = Settings.llm or llm_client
            result = await llm.complete(
                prompt=f"""请评估以下对话的重要性，输出一个 1-10 的整数分数。

评分标准：
- 1-3: 闲聊、问候、无实质内容
- 4-5: 普通问答、信息查询
- 6-7: 涉及决策、偏好、重要信息、工具使用
- 8-9: 关键决策、用户明确要求记住、重要发现
- 10: 极其重要（如密码、关键配置、重大变更）

对话内容:
{text[:3000]}

只输出一个数字（1-10），不要其他内容。""",
            )

            score_str = result.text.strip()
            # 提取数字
            import re
            match = re.search(r'\d+', score_str)
            if match:
                return max(1, min(10, int(match.group())))
            return 5

        except Exception as e:
            logger.warning(f"LLM 评分失败，降级为关键词: {e}")
            return MemoryManager._score_conversation_importance(messages)

    async def _check_consolidation(
        self, summary: str, user_id: int, tags: list, importance: int,
        network: str, conversation_id: int, message_count: int,
    ) -> Optional[dict]:
        """写入前检查是否有相似记忆需要合并

        v5.1: 借鉴 Mem0/Zep 的写入前合并策略。
        相似度 >0.85 时由 LLM 判断 keep/update/delete/insert_new。

        Returns:
            合并后的结果 dict（如果执行了合并），否则 None
        """
        try:
            from app.services.memory_consolidation_service import (
                MemoryConsolidationService, MergeDecision
            )

            consolidation = MemoryConsolidationService(
                qdrant_mapper=self.qdrant,
                embedding_func=self.embedding_func,
                llm_client=self.llm,
            )

            # 查找相似记忆
            similar = await consolidation.find_similar(
                text=summary,
                user_id=user_id,
                threshold=0.85,
                limit=1,
            )

            if not similar:
                return None  # 无相似记忆，走正常写入流程

            existing = similar[0]
            logger.info(
                f"[consolidation] 发现相似记忆(score={similar[0]['score']:.2f}), "
                f"执行合并决策"
            )

            # 执行合并决策
            result = await consolidation.consolidate_pair(
                existing=existing,
                new_text=summary,
                user_id=user_id,
            )

            action = result["action"]

            if action == MergeDecision.KEEP:
                # 保留旧的，不写入新的
                logger.info(f"[consolidation] 决策: keep — 保留已有记忆")
                return {
                    "point_id": existing["id"],
                    "summary": existing.get("summary", ""),
                    "tags": existing.get("tags", []),
                    "importance": existing.get("importance", importance),
                    "consolidated": "keep",
                }

            elif action == MergeDecision.UPDATE:
                # 已合并并写入新 point
                logger.info(f"[consolidation] 决策: update — 已合并为新记忆")
                return {
                    "point_id": result.get("new_point_id", ""),
                    "summary": summary,  # 简化返回
                    "tags": tags,
                    "importance": importance,
                    "consolidated": "update",
                }

            elif action == MergeDecision.DELETE:
                # v5.1 fix: 返回 _write_new 标记 + _pending_delete_ids
                # 调用方先写入新记忆，成功后再删除旧的
                logger.info(f"[consolidation] 决策: delete — 写入新的后删除旧的")
                return {
                    "_write_new": True,
                    "_pending_delete_ids": result.get("pending_delete_ids", []),
                    "point_id": "",  # 写入后填充
                    "summary": summary,
                    "tags": tags,
                    "importance": importance,
                    "consolidated": "delete",
                }

            else:  # INSERT_NEW
                logger.info(f"[consolidation] 决策: insert_new — 两条都保留")
                return None  # 继续写入新记忆

        except Exception as e:
            logger.warning(f"[consolidation] 合并检查失败（降级为直接写入）: {e}")
            return None  # 失败时降级为正常写入

    async def save_memory(self, user_id: int, summary: str, tags: list = None,
                          importance: int = 5, network: str = "world",
                          freshness: str = "", parent_point_id: str = "") -> str:
        """保存用户主动创建的记忆

        v5.1: 新增 freshness 参数，同步 observation 新鲜度到 Qdrant payload。
        v5.2: 新增 parent_point_id，支持记忆进化链追踪。
        """
        vector = await self.embedding_func(summary)
        point_id = str(uuid.uuid4())

        payload = {
            "type": "user_memory",
            "network": network,
            "user_id": user_id,
            "summary": summary,
            "tags": tags or [],
            "importance": importance,
            "activation": 1.0,
            "decay_status": "active",
            "saved_at": datetime.utcnow().isoformat(),
            "evidence_count": 1,
            "confidence": 1.0,
        }
        if freshness:
            payload["freshness"] = freshness
        if parent_point_id:
            payload["parent_point_id"] = parent_point_id

        self.qdrant.upsert(
            collection=MEMORY_COLLECTION,
            point_id=point_id,
            vector=vector,
            payload=payload,
        )
        return point_id

    # ── 语义检索（v4.0: 4 路并行 + RRF 融合 + Token 预算）──

    async def search(self, query: str, user_id: int, limit: int = 5,
                     max_tokens: int = 0) -> str:
        """检索相关记忆 — v4.0 多策略融合

        Args:
            query: 查询文本
            user_id: 用户 ID
            limit: 最大返回条数
            max_tokens: Token 预算（0=不限制，>0=按 token 填充）
        """
        results = await self.search_with_scores(query, user_id, limit)

        if not results:
            return ""

        parts = []
        token_count = 0
        for r in results:
            ptype = r.get("type", "detail")
            score = r.get("score", 0)
            network = r.get("network", "")
            network_tag = f"|{network}" if network else ""

            if ptype in ("summary", "user_memory"):
                text = r.get("summary", "")
            else:
                msg_count = len(r.get("messages", []))
                text = f"对话记录 ({msg_count}条消息)"

            # P2-9: Token 预算过滤
            if max_tokens > 0:
                est_tokens = len(text) // 2  # 粗略估算
                if token_count + est_tokens > max_tokens:
                    break
                token_count += est_tokens

            parts.append(f"[记忆{network_tag} | 相关度:{score:.2f} | {r.get('saved_at', '')}] {text}")

        return "\n".join(parts)

    async def search_with_scores(
        self, query: str, user_id: int, limit: int = 10,
        rerank: bool = True, decay: bool = True,
    ) -> List[dict]:
        """检索记忆并返回带分数的结果

        v4.0 多策略融合（借鉴 Hindsight TEMPR Recall）:
          1. 语义检索（Qdrant 向量余弦）
          2. 关键词检索（Qdrant BM25 全文）
          3. 标签图遍历（共享 tag 的关联记忆）
          4. 时间范围检索（检测查询中的时间约束）
          → RRF 融合 4 路结果
          → 时间衰减
          → MMR 去重
          → Top-K

        Args:
            rerank: 是否启用 Cross-Encoder 精排
            decay: 是否启用时间衰减
        """
        query_vector = await self.embedding_func(query)

        from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchText

        user_filter = Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            # v5.0: 过滤 dormant 记忆（认知衰减机制）
            FieldCondition(key="decay_status", match=MatchValue(value="active")),
        ]) if user_id else Filter(must=[
            FieldCondition(key="decay_status", match=MatchValue(value="active")),
        ])

        # ── Channel 1: 语义检索（向量余弦）──
        vector_results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=query_vector,
            limit=limit * 4,
            score_threshold=0.2,
            raw_filter=user_filter,
        )
        ch1 = self._to_candidates(vector_results, channel="semantic")

        # ── Channel 2: 关键词检索（BM25 全文）──
        query_terms = [t.strip() for t in query.lower().split() if len(t.strip()) >= 2]
        ch2 = []
        if query_terms:
            text_conditions = [
                FieldCondition(key="summary", match=MatchText(text=term))
                for term in query_terms[:5]
            ]
            bm25_filter = Filter(
                must=[user_filter],
                should=text_conditions,
            ) if user_filter else Filter(should=text_conditions)

            bm25_results = self.qdrant.search(
                collection=MEMORY_COLLECTION,
                query_vector=query_vector,
                limit=limit * 2,
                score_threshold=0.1,
                raw_filter=bm25_filter,
            )
            ch2 = self._to_candidates(bm25_results, channel="keyword")

        # ── Channel 3: 标签图遍历（共享 tag 的关联记忆）──
        ch3 = []
        if ch1:
            top_tags = set()
            for c in ch1[:5]:
                for t in (c.get("tags") or []):
                    top_tags.add(t)
            if top_tags:
                for tag in list(top_tags)[:3]:
                    tag_filter = Filter(must=[
                        *([FieldCondition(key="user_id", match=MatchValue(value=user_id))] if user_filter else []),
                        FieldCondition(key="tags", match=MatchValue(value=tag)),
                    ])
                    try:
                        tag_results = self.qdrant.search(
                            collection=MEMORY_COLLECTION,
                            query_vector=query_vector,
                            limit=limit,
                            score_threshold=0.15,
                            raw_filter=tag_filter,
                        )
                        ch3.extend(self._to_candidates(tag_results, channel="graph"))
                    except Exception:
                        pass

        # ── Channel 4: 时间范围检索 ──
        ch4 = []
        time_range = self._parse_time_query(query)
        if time_range:
            start_str, end_str = time_range
            time_filter = Filter(must=[
                *([FieldCondition(key="user_id", match=MatchValue(value=user_id))] if user_filter else []),
                FieldCondition(key="saved_at", range={"gte": start_str, "lte": end_str}),
            ]) if user_filter else Filter(must=[
                FieldCondition(key="saved_at", range={"gte": start_str, "lte": end_str}),
            ])
            try:
                time_results = self.qdrant.search(
                    collection=MEMORY_COLLECTION,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=0.1,
                    raw_filter=time_filter,
                )
                ch4 = self._to_candidates(time_results, channel="temporal")
            except Exception:
                pass

        # ── v5.1 Channel 5: 实体图遍历（实体关联记忆召回）──
        ch5 = await self._entity_graph_search(query, query_vector, user_id, limit)

        # ── RRF 融合（Reciprocal Rank Fusion）──
        channels = [ch1, ch2, ch3, ch4, ch5]
        fused = self._rrf_fusion(channels, k=60)

        # ── v5.0 Cross-Encoder Rerank（先精排）──
        if rerank and len(fused) > 1:
            fused = await self._apply_rerank(fused, query, top_n=min(20, len(fused)))

        # ── 时间衰减（结合持久化 activation + importance 动态半衰期）──
        if decay:
            fused = self._apply_temporal_decay(fused, half_life_days=30)

        # ── MMR 去重（后多样化）──
        fused = self._apply_mmr(fused, query, lambda_param=0.7)

        # ── v5.1: Stale Observation 降权（freshness=stale 的记忆 score * 0.5）──
        fused = self._apply_stale_penalty(fused)

        result = fused[:limit]

        # ── v5.0: fire-and-forget 记录 access_count（top-K 命中）──
        if result:
            try:
                self._record_access_batch([r.get("id", "") for r in result if r.get("id")])
            except Exception:
                pass

        return result

    # ── v5.0 Cross-Encoder Rerank ────────────────────────

    async def _apply_rerank(self, results: List[dict], query: str, top_n: int = 20) -> List[dict]:
        """Cross-Encoder 精排（借鉴 Hindsight TEMPR + ConvMemory）

        仅对 top-N 候选做 cross-encoder 打分（控制延迟）。
        混合: final = 0.6 * rerank_score + 0.4 * norm_original
        降级: reranker=None 时用 embedding cosine 做轻量精排。
        """
        candidates = results[:top_n]
        rest = results[top_n:]

        # 提取 candidate 文本（截取 512 字符）
        texts = []
        for c in candidates:
            text = c.get("summary", "") or ""
            if not text and c.get("messages"):
                text = f"对话记录 ({len(c['messages'])} 条消息)"
            texts.append(text[:512])

        rerank_scores: List[float] = []
        if self.reranker:
            try:
                rerank_scores = await self.reranker.rerank(query, texts)
            except Exception as e:
                logger.warning(f"[rerank] ONNX reranker 失败，降级: {e}")
                rerank_scores = []

        # 降级: embedding cosine 做轻量精排
        if not rerank_scores or len(rerank_scores) != len(candidates):
            rerank_scores = self._jaccard_keyword_rerank(query, texts)

        # Min-Max 归一化原始 RRF 分数
        raw_scores = [c.get("score", 0) for c in candidates]
        min_s, max_s = min(raw_scores) if raw_scores else 0, max(raw_scores) if raw_scores else 1
        score_range = max_s - min_s if max_s != min_s else 1.0

        for i, cand in enumerate(candidates):
            norm_orig = (raw_scores[i] - min_s) / score_range if score_range > 0 else 0.5
            rs = rerank_scores[i] if i < len(rerank_scores) else 0.5
            cand["score"] = 0.6 * rs + 0.4 * norm_orig
            cand["rerank_score"] = rs

        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        return candidates + rest

    def _jaccard_keyword_rerank(self, query: str, texts: List[str]) -> List[float]:
        """降级 rerank: 基于 Jaccard 相似度的轻量精排（|A∩B| / |A∪B|）"""
        if not texts:
            return []
        query_words = set(query.lower().split())
        scores = []
        for text in texts:
            text_words = set(text.lower().split())
            if not query_words or not text_words:
                scores.append(0.0)
                continue
            intersection = query_words & text_words
            union_size = len(query_words | text_words)
            scores.append(len(intersection) / union_size if union_size > 0 else 0.0)
        return scores

    # ── 时间衰减（v5.0: 结合持久化 activation + importance 动态半衰期）──

    def _apply_temporal_decay(self, results: List[dict], half_life_days: int = 30) -> List[dict]:
        """时间衰减 — v5.0 结合持久化 activation + importance 动态半衰期

        公式: decayed_score = score × stored_activation × e^(-λ_dynamic × age_days)
        动态半衰期: half_life = 30天 × (importance / 5.0)
        importance=10 → 60天半衰期; importance=1 → 6天半衰期
        """
        now = datetime.utcnow()

        for r in results:
            saved_at = r.get("saved_at", "")
            if not saved_at:
                continue
            try:
                saved_dt = datetime.fromisoformat(saved_at.replace("Z", "+00:00").replace("+00:00", ""))
                age_days = (now - saved_dt).total_seconds() / 86400

                # v5.0: importance 动态半衰期
                importance = r.get("importance", 5)
                dynamic_half_life = half_life_days * (importance / 5.0)
                lambda_dynamic = math.log(2) / max(dynamic_half_life, 1)

                # v5.0: 持久化 activation（从 Qdrant payload 读，默认 1.0）
                stored_activation = float(r.get("activation", 1.0))

                decay_factor = stored_activation * math.exp(-lambda_dynamic * age_days)
                r["score"] = r.get("score", 0) * decay_factor
                r["decay_factor"] = decay_factor

                # 多源置信度加成：evidence_count 越多，confidence 越高
                confidence = float(r.get("confidence", 1.0))
                evidence_count = int(r.get("evidence_count", 1))
                confidence_boost = 1.0 + (evidence_count - 1) * 0.05  # 每多一个证据 +5%
                r["score"] = r.get("score", 0) * min(confidence_boost, 1.5)  # 最高 1.5x
                r["confidence_boost"] = min(confidence_boost, 1.5)
            except (ValueError, TypeError):
                pass

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results

    # ── v5.1: Stale Observation 降权 ──────────────────────

    @staticmethod
    def _apply_stale_penalty(results: List[dict]) -> List[dict]:
        """Stale observation 降权: freshness=stale 的记忆 score * 0.5

        仅对 payload 中有 freshness=stale 的记忆生效。
        其他记忆不受影响。
        """
        STALE_PENALTY = 0.5
        for r in results:
            if r.get("freshness") == "stale":
                r["score"] = r.get("score", 0) * STALE_PENALTY
                r["stale_penalized"] = True
        # 重新排序（stale 降权后可能低于其他结果）
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

    # ── v4.0 辅助方法 ──────────────────────────────

    @staticmethod
    def _to_candidates(results, channel: str = "") -> List[dict]:
        """将 Qdrant 搜索结果转为标准 candidate 格式"""
        candidates = []
        for r in (results or []):
            candidates.append({
                "id": r.id,
                "score": r.score,
                "type": r.payload.get("type", "detail"),
                "network": r.payload.get("network", ""),
                "summary": r.payload.get("summary", ""),
                "tags": r.payload.get("tags", []),
                "importance": r.payload.get("importance", 5),
                "activation": r.payload.get("activation", 1.0),
                "decay_status": r.payload.get("decay_status", "active"),
                "freshness": r.payload.get("freshness", ""),
                "saved_at": r.payload.get("saved_at", ""),
                "messages": r.payload.get("messages", []),
                "channel": channel,
            })
        return candidates

    @staticmethod
    def _rrf_fusion(channels: List[List[dict]], k: int = 60) -> List[dict]:
        """Reciprocal Rank Fusion — 借鉴 Hindsight TEMPR RRF

        公式: RRF(d) = Σ 1/(k + rank_i(d))  对所有 channel i
        优点: 不依赖分数校准，跨通道可比，缺失通道不惩罚
        """
        score_map: dict[str, float] = {}  # id → rrf score
        cand_map: dict[str, dict] = {}    # id → candidate

        for channel in channels:
            for rank, cand in enumerate(channel):
                cid = cand.get("id", "")
                if not cid:
                    continue
                rrf_score = 1.0 / (k + rank + 1)
                score_map[cid] = score_map.get(cid, 0.0) + rrf_score
                if cid not in cand_map:
                    cand_map[cid] = cand

        # 按 RRF 分数排序
        sorted_ids = sorted(score_map.keys(), key=lambda x: score_map[x], reverse=True)
        result = []
        for cid in sorted_ids:
            cand = cand_map[cid]
            cand["score"] = score_map[cid]  # 用 RRF 分数替代原始分数
            result.append(cand)
        return result

    @staticmethod
    def _parse_time_query(query: str) -> Optional[tuple]:
        """解析查询中的时间约束（简化版）

        支持: "上周"、"本月"、"最近三天"、"六月"、"last week"、"today"
        返回: (start_iso, end_iso) 或 None
        """
        from datetime import timedelta
        now = datetime.utcnow()
        q = query.lower()

        # 中文时间表达
        if "上周" in q or "上个星期" in q:
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=6)
            return (start.strftime("%Y-%m-%dT00:00:00"), end.strftime("%Y-%m-%dT23:59:59"))
        if "本周" in q or "这周" in q or "这星期" in q:
            start = now - timedelta(days=now.weekday())
            return (start.strftime("%Y-%m-%dT00:00:00"), now.strftime("%Y-%m-%dT23:59:59"))
        if "昨天" in q or "昨日" in q:
            yesterday = now - timedelta(days=1)
            return (yesterday.strftime("%Y-%m-%dT00:00:00"), yesterday.strftime("%Y-%m-%dT23:59:59"))
        if "今天" in q or "今日" in q:
            return (now.strftime("%Y-%m-%dT00:00:00"), now.strftime("%Y-%m-%dT23:59:59"))
        if "上月" in q or "上个月" in q:
            first = now.replace(day=1) - timedelta(days=1)
            first = first.replace(day=1)
            last = now.replace(day=1) - timedelta(days=1)
            return (first.strftime("%Y-%m-%dT00:00:00"), last.strftime("%Y-%m-%dT23:59:59"))
        if "本月" in q or "这个月" in q:
            return (now.strftime("%Y-%m-01T00:00:00"), now.strftime("%Y-%m-%dT23:59:59"))

        # “最近 N 天”
        import re
        match = re.search(r"最近\s*(\d+)\s*天", q)
        if match:
            days = int(match.group(1))
            start = now - timedelta(days=days)
            return (start.strftime("%Y-%m-%dT00:00:00"), now.strftime("%Y-%m-%dT23:59:59"))

        # 英文
        if "last week" in q:
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=6)
            return (start.strftime("%Y-%m-%dT00:00:00"), end.strftime("%Y-%m-%dT23:59:59"))
        if "today" in q:
            return (now.strftime("%Y-%m-%dT00:00:00"), now.strftime("%Y-%m-%dT23:59:59"))
        if "yesterday" in q:
            yesterday = now - timedelta(days=1)
            return (yesterday.strftime("%Y-%m-%dT00:00:00"), yesterday.strftime("%Y-%m-%dT23:59:59"))

        return None

    @staticmethod
    def _classify_network(summary: str, tags: list) -> str:
        """将记忆分类到 4 网络（借鉴 Hindsight 4-Network）

        world: 客观事实（技术信息、项目状态）
        experience: Agent 自身经验（调试、解决问题）
        opinion: 主观判断（偏好、推荐、评价）
        observation: 实体摘要（综合信息）

        当前用启发式规则，后续可改为 LLM 分类
        """
        text = (summary + " " + " ".join(tags or [])).lower()

        # 经验类关键词
        exp_keywords = ["调试", "排查", "解决", "修复", "踩坑", "错误", "失败", "经验",
                        "debug", "fix", "error", "issue", "troubleshoot"]
        if any(kw in text for kw in exp_keywords):
            return "experience"

        # 观点类关键词
        opinion_keywords = ["建议", "推荐", "偏好", "喜欢", "应该", "最好", "觉得",
                            "认为", "不推荐", "recommend", "prefer", "better", "should"]
        if any(kw in text for kw in opinion_keywords):
            return "opinion"

        # 默认 world（客观事实）
        return "world"

    # ── v5.1 实体图检索 ────────────────────────────────

    async def _entity_graph_search(
        self, query: str, query_vector: list, user_id: int, limit: int,
    ) -> List[dict]:
        """Channel 5: 实体图遍历 — 通过实体关系扩展检索

        流程:
          1. 从 query 提取词项
          2. 在 MySQL MemoryEntity 中匹配（name + aliases）
          3. 通过 MemoryEntityRelation 扩展 1 跳邻居
          4. 用所有实体名称在 Qdrant 中搜索（summary 全文匹配）

        Returns:
            candidate 列表（可能为空）
        """
        query_terms = self._extract_query_terms(query)
        if not query_terms:
            return []

        try:
            from app.core.database import AsyncSessionLocal
            from app.repository.memory_entity_repo import MemoryEntityRepository

            repo = MemoryEntityRepository()
            async with AsyncSessionLocal() as db:
                # Step 1: 匹配 query 中的实体
                seed_entities = await repo.find_by_names(db, query_terms, user_id)
                if not seed_entities:
                    return []

                # Step 2: 通过关系图扩展 1 跳邻居
                all_entities = await repo.expand_neighbors(
                    db, [e.id for e in seed_entities], user_id, max_hops=1,
                )

            # Step 3: 收集所有实体名 + 别名（去重，截断到 20 个）
            entity_names = set()
            for ent in all_entities:
                entity_names.add(ent.name.lower())
                for alias in (ent.aliases or "").split(","):
                    alias = alias.strip()
                    if alias and len(alias) >= 2:
                        entity_names.add(alias.lower())
            entity_names = list(entity_names)[:20]

            if not entity_names:
                return []

            # Step 4: 在 Qdrant 中搜索包含这些实体名的记忆
            from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchText

            entity_conditions = [
                FieldCondition(key="summary", match=MatchText(text=name))
                for name in entity_names
            ]
            entity_filter = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))] if user_id else [],
                should=entity_conditions,
            )

            results = self.qdrant.search(
                collection=MEMORY_COLLECTION,
                query_vector=query_vector,
                limit=limit * 2,
                score_threshold=0.1,
                raw_filter=entity_filter,
            )
            return self._to_candidates(results, channel="entity_graph")

        except Exception as e:
            logger.debug(f"[Channel 5] 实体图检索失败: {e}")
            return []

    @staticmethod
    def _extract_query_terms(query: str) -> List[str]:
        """从查询中提取潜在实体名（用于实体图匹配）

        启发式策略:
          - 英文: 大写词 + 长度>=3 的词
          - 中文: 2-6 字的词
        """
        import re
        terms = []

        # 英文大写词（可能是专有名词）
        for word in query.split():
            cleaned = word.strip(".,!?()[]{}\"'")
            if len(cleaned) >= 3 and (cleaned[0].isupper() or cleaned.isupper()):
                terms.append(cleaned)

        # 中文 2-6 字片段
        chinese_segments = re.findall(r'[\u4e00-\u9fa5]{2,6}', query)
        terms.extend(chinese_segments)

        # 去重，最多返回 10 个
        seen = set()
        unique_terms = []
        for t in terms:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_terms.append(t)
        return unique_terms[:10]

    def _record_access_batch(self, point_ids: List[str]):
        """fire-and-forget: 记录检索命中（更新 Qdrant payload 的 access_count + last_accessed_at）

        注意: 先读取当前 access_count 再递增写回，保证 ACT-R 激活度模型有效。
        """
        now_iso = datetime.utcnow().isoformat()
        for pid in point_ids:
            try:
                # 先读取当前 access_count
                point = self.qdrant._client.get_point(MEMORY_COLLECTION, pid)
                current_count = int((point.payload or {}).get("access_count", 0))
                self.qdrant._client.set_payload(
                    collection_name=MEMORY_COLLECTION,
                    payload={
                        "last_accessed_at": now_iso,
                        "access_count": current_count + 1,
                    },
                    points=[pid],
                )
            except Exception:
                pass  # fire-and-forget

    # ── v5.0 经历操作 ────────────────────────────────

    async def save_episode(
        self, user_id: int, conversation_id: int, title: str, summary: str,
        started_at: str, ended_at: str, message_count: int = 0,
        entity_ids: List[int] = None, tags: list = None,
    ) -> str:
        """保存经历到 Qdrant（bi-temporal + entity keyword 索引）

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
                "type": "episode",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "title": title,
                "summary": summary,
                "started_at": started_at,
                "ended_at": ended_at,
                "message_count": message_count,
                "entity_ids": ",".join(str(e) for e in (entity_ids or [])),
                "tags": tags or [],
                "importance": 7,
                "activation": 1.0,
                "decay_status": "active",
                "saved_at": datetime.utcnow().isoformat(),
            },
        )
        logger.info(f"[经历] Qdrant 已保存: conv={conversation_id} title={title[:30]}")
        return point_id

    def find_episodes_by_entity(self, entity_id: int, user_id: int = 0, limit: int = 10) -> List[dict]:
        """按实体 ID 查找关联经历（Qdrant keyword 匹配）"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        conditions = [
            FieldCondition(key="type", match=MatchValue(value="episode")),
            FieldCondition(key="entity_ids", match=MatchValue(value=str(entity_id))),
        ]
        if user_id:
            conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
        ep_filter = Filter(must=conditions)

        results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=[0.0] * 1024,  # dummy vector, 靠 filter 筛选
            limit=limit,
            score_threshold=0.0,
            raw_filter=ep_filter,
        )
        return [
            {
                "id": r.id,
                "title": r.payload.get("title", ""),
                "summary": r.payload.get("summary", ""),
                "conversation_id": r.payload.get("conversation_id", 0),
                "started_at": r.payload.get("started_at", ""),
                "ended_at": r.payload.get("ended_at", ""),
                "tags": r.payload.get("tags", []),
            }
            for r in results
        ]

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

    # ── v5.2: 主动回忆注入 ──────────────────────────────

    async def proactive_recall(self, user_id: int, max_items: int = 3) -> str:
        """主动回忆 — 扫描高价值、低访问的记忆，在对话开头注入提醒

        借鉴 Hindsight 的「主动回忆」机制：
        - 高重要性（>=7）+ 活跃状态 + 长时间未访问（>7天）
        - 按 confidence × importance 排序
        - 返回格式化的提醒文本

        Returns:
            格式化的主动回忆文本，无相关内容返回空字符串
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
        from datetime import datetime, timedelta

        try:
            cutoff = datetime.utcnow() - timedelta(days=7)
            cutoff_str = cutoff.isoformat()

            # 筛选：高重要性 + 活跃 + 长时间未访问
            conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="decay_status", match=MatchValue(value="active")),
                FieldCondition(key="importance", range=Range(gte=7)),
                FieldCondition(key="type", match=MatchValue(value="summary")),
            ]

            # scroll 查找候选记忆（不用 search，因为需要 filter 而非向量）
            points, _ = self.qdrant._client.scroll(
                collection_name=MEMORY_COLLECTION,
                scroll_filter=Filter(must=conditions),
                limit=50,
                with_vectors=False,
            )

            if not points:
                return ""

            # 过滤：access_count 低 或 last_accessed_at 早于 cutoff
            candidates = []
            for p in points:
                payload = p.payload or {}
                last_accessed = payload.get("last_accessed_at", "")
                access_count = int(payload.get("access_count", 0))

                # 低访问：从未访问 或 超过 7 天未访问
                should_include = False
                if access_count == 0:
                    should_include = True
                elif last_accessed:
                    try:
                        last_dt = datetime.fromisoformat(
                            last_accessed.replace("Z", "+00:00").replace("+00:00", "")
                        )
                        if last_dt < cutoff:
                            should_include = True
                    except (ValueError, TypeError):
                        should_include = True

                if should_include:
                    confidence = float(payload.get("confidence", 1.0))
                    importance = int(payload.get("importance", 5))
                    candidates.append({
                        "id": p.id,
                        "summary": payload.get("summary", ""),
                        "score": confidence * importance,
                        "saved_at": payload.get("saved_at", ""),
                    })

            if not candidates:
                return ""

            # 按 score 排序，取 top N
            candidates.sort(key=lambda x: x["score"], reverse=True)
            top = candidates[:max_items]

            # 格式化
            parts = []
            for item in top:
                summary = item["summary"][:200]
                parts.append(f"- {summary}")

            return (
                "\n\n【主动回忆】以下是你之前记录的重要信息，可能与当前对话相关：\n"
                + "\n".join(parts)
            )

        except Exception as e:
            logger.warning(f"主动回忆失败(非致命): {e}")
            return ""
