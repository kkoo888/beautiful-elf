"""Sleep-Time Compute Agent — 后台深度记忆整理

借鉴 Letta MemGPT 2.0 sleep-time compute 理念。
Agent 空闲时（每日凌晨）执行三阶段记忆整理:

Phase A 碎片合并: 扫描近 7 天 detail/summary，LLM 判断合并去重
Phase B 知识图谱更新: 对合并产生的新 summary 执行实体 + 关系抽取
Phase C 洞察触发: 发现矛盾/新模式时自动触发 reflect()

设计原则:
  - 幂等: 标记 consolidated 避免重复处理
  - 可配置: SLEEPTIME_MODEL 可使用更强模型
  - 容错: 每阶段独立 try/except，单条失败不影响整体
  - 限流: 单次最多处理 200 条记忆
"""
from datetime import datetime, timedelta
from typing import List

from app.core.logging import get_logger

logger = get_logger(__name__)

MEMORY_COLLECTION = "memory_vectors"


class SleepTimeAgent:
    """Sleep-Time Compute Agent

    后台记忆整理代理，每日凌晨执行。
    """

    def __init__(self, qdrant_mapper, embedding_func, llm_client=None, max_items: int = 200):
        """
        Args:
            qdrant_mapper: QdrantMapper 实例
            embedding_func: async embedding 函数
            llm_client: LlamaIndex LLM 实例（可配置更强模型）
            max_items: 单次最多处理条数
        """
        self.qdrant = qdrant_mapper
        self.embedding_func = embedding_func
        self.llm = llm_client
        self.max_items = max_items

    async def run(self, user_id: int = 0) -> dict:
        """执行完整的 sleep-time compute 管线

        Returns:
            {
                "phase_a": {merged, deleted, kept},
                "phase_b": {entities_created, relations_created},
                "phase_c": {insights_created},
                "duration_seconds": float,
            }
        """
        start_time = datetime.utcnow()
        result = {
            "phase_a": {"merged": 0, "deleted": 0, "kept": 0},
            "phase_b": {"entities_created": 0, "relations_created": 0},
            "phase_c": {"insights_created": 0},
            "duration_seconds": 0,
        }

        # ── Phase A: 碎片合并 ──
        try:
            result["phase_a"] = await self._phase_a_consolidate(user_id)
            logger.info(f"[SleepTime] Phase A 完成: {result['phase_a']}")
        except Exception as e:
            logger.error(f"[SleepTime] Phase A 失败: {e}")

        # ── Phase B: 知识图谱更新 ──
        try:
            result["phase_b"] = await self._phase_b_entity_extract(user_id)
            logger.info(f"[SleepTime] Phase B 完成: {result['phase_b']}")
        except Exception as e:
            logger.error(f"[SleepTime] Phase B 失败: {e}")

        # ── Phase C: 洞察触发 ──
        try:
            result["phase_c"] = await self._phase_c_insight_trigger(user_id)
            logger.info(f"[SleepTime] Phase C 完成: {result['phase_c']}")
        except Exception as e:
            logger.error(f"[SleepTime] Phase C 失败: {e}")

        result["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
        return result

    async def _phase_a_consolidate(self, user_id: int) -> dict:
        """Phase A: 碎片合并

        扫描近 7 天未合并的 detail/summary，执行 LLM 合并去重。
        """
        from app.services.memory_consolidation_service import MemoryConsolidationService

        consolidation = MemoryConsolidationService(
            qdrant_mapper=self.qdrant,
            embedding_func=self.embedding_func,
            llm_client=self.llm,
        )

        # 查找近 7 天未合并的记忆
        items = await self._list_unconsolidated(user_id, days=7, limit=self.max_items)
        if not items:
            logger.info("[SleepTime] Phase A: 无待合并记忆")
            return {"merged": 0, "deleted": 0, "kept": 0}

        logger.info(f"[SleepTime] Phase A: 找到 {len(items)} 条待合并记忆")

        # 按类型分组：先合并 detail，再合并 summary
        details = [i for i in items if i.get("type") == "detail"]
        summaries = [i for i in items if i.get("type") == "summary"]

        stats = {"merged": 0, "deleted": 0, "kept": 0}

        if details:
            detail_stats = await consolidation.batch_consolidate(details, user_id)
            for k in stats:
                stats[k] += detail_stats.get(k, 0)

        if summaries:
            summary_stats = await consolidation.batch_consolidate(summaries, user_id)
            for k in stats:
                stats[k] += summary_stats.get(k, 0)

        return stats

    async def _phase_b_entity_extract(self, user_id: int) -> dict:
        """Phase B: 知识图谱更新

        对新合并产生的 summary 执行实体 + 关系抽取。
        查找最近 24 小时内 consolidated=True 但 entity_extracted!=True 的记忆。
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        conditions = [
            FieldCondition(key="consolidated", match=MatchValue(value=True)),
        ]
        if user_id:
            conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))

        search_filter = Filter(must=conditions)

        results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=[0.0] * 1024,  # dummy vector
            limit=50,
            score_threshold=0.0,
            raw_filter=search_filter,
        )

        # 过滤：只处理 entity_extracted 不为 True 且 saved_at 在 24 小时内
        candidates = []
        for r in results:
            payload = r.payload or {}
            if payload.get("entity_extracted"):
                continue
            saved_at = payload.get("saved_at", "")
            if saved_at and saved_at >= cutoff:
                candidates.append(r)

        if not candidates:
            logger.info("[SleepTime] Phase B: 无待抽取实体")
            return {"entities_created": 0, "relations_created": 0}

        logger.info(f"[SleepTime] Phase B: 找到 {len(candidates)} 条待抽取记忆")

        # 调用实体抽取
        total_entities = 0
        total_relations = 0

        try:
            from app.core.database import AsyncSessionLocal
            from app.services.markdown_memory_service import markdown_memory_service

            async with AsyncSessionLocal() as db:
                for r in candidates[:20]:  # 限制单次抽取数量
                    summary = (r.payload or {}).get("summary", "")
                    if not summary:
                        continue

                    # 构造一个伪 Observation 对象用于实体抽取
                    # extract_entities 需要 MemoryObservation 列表
                    # 这里直接调用底层实体创建逻辑
                    try:
                        stats = await self._extract_from_summary(db, summary, user_id)
                        total_entities += stats.get("entities", 0)
                        total_relations += stats.get("relations", 0)

                        # 标记 entity_extracted = True
                        self.qdrant._client.set_payload(
                            collection_name=MEMORY_COLLECTION,
                            payload={"entity_extracted": True},
                            points=[r.id],
                        )
                    except Exception as e:
                        logger.warning(f"[SleepTime] Phase B 单条抽取失败: {e}")

                await db.commit()

        except Exception as e:
            logger.warning(f"[SleepTime] Phase B 实体抽取失败: {e}")

        return {"entities_created": total_entities, "relations_created": total_relations}

    async def _extract_from_summary(self, db, summary: str, user_id: int) -> dict:
        """从 summary 文本抽取实体和关系（简化版）

        复用 markdown_memory_service 的实体抽取逻辑。
        """
        try:
            from app.agent.llm_service import llm_service
            from app.models.memory_entity import MemoryEntity
            from app.models.memory_entity_relation import MemoryEntityRelation
            from sqlalchemy import select

            # 使用 LLM 抽取实体和关系
            llm = await llm_service.get_chat_llm(db, temperature=0.2)

            prompt = f"""从以下文本中提取实体和它们之间的关系。

文本: {summary[:2000]}

请输出 JSON 格式:
{{"entities": [{{"name": "实体名", "type": "person|project|tech|concept|location", "aliases": "别名1,别名2"}}],
  "relations": [{{"source": "源实体名", "target": "目标实体名", "relation_type": "关系类型"}}]}}"""

            result = await llm.complete(prompt=prompt)
            text = result.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            import json
            data = json.loads(text)

            # 创建实体
            entity_map = {}  # name -> entity
            entities_created = 0
            for ent_data in data.get("entities", [])[:10]:
                name = ent_data.get("name", "").strip()
                if not name:
                    continue

                # 检查是否已存在
                stmt = select(MemoryEntity).where(
                    MemoryEntity.name == name,
                    MemoryEntity.is_deleted == 0,
                )
                if user_id:
                    stmt = stmt.where(MemoryEntity.user_id == user_id)
                existing = (await db.execute(stmt)).scalar_one_or_none()

                if existing:
                    entity_map[name.lower()] = existing
                else:
                    new_entity = MemoryEntity(
                        name=name,
                        entity_type=ent_data.get("type", "concept"),
                        aliases=ent_data.get("aliases", ""),
                        user_id=user_id,
                    )
                    db.add(new_entity)
                    await db.flush()
                    entity_map[name.lower()] = new_entity
                    entities_created += 1

            # 创建关系
            relations_created = 0
            for rel_data in data.get("relations", [])[:20]:
                source_name = rel_data.get("source", "").strip().lower()
                target_name = rel_data.get("target", "").strip().lower()
                if not source_name or not target_name:
                    continue

                source = entity_map.get(source_name)
                target = entity_map.get(target_name)
                if not source or not target:
                    continue

                # 检查是否已存在
                stmt = select(MemoryEntityRelation).where(
                    MemoryEntityRelation.source_entity_id == source.id,
                    MemoryEntityRelation.target_entity_id == target.id,
                    MemoryEntityRelation.is_deleted == 0,
                )
                existing_rel = (await db.execute(stmt)).scalar_one_or_none()
                if existing_rel:
                    continue

                new_rel = MemoryEntityRelation(
                    source_entity_id=source.id,
                    target_entity_id=target.id,
                    relation_type=rel_data.get("relation_type", "related_to"),
                    user_id=user_id,
                )
                db.add(new_rel)
                relations_created += 1

            return {"entities": entities_created, "relations": relations_created}

        except Exception as e:
            logger.warning(f"[SleepTime] 实体抽取失败: {e}")
            return {"entities": 0, "relations": 0}

    async def _phase_c_insight_trigger(self, user_id: int) -> dict:
        """Phase C: 洞察触发

        当发现矛盾或新模式时，触发 reflect() 生成深度 Insight。
        启发式: 查找近 7 天 importance >= 7 且未被 insight 覆盖的记忆。
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()

        conditions = [
            FieldCondition(key="importance", range=Range(gte=7)),
            FieldCondition(key="decay_status", match=MatchValue(value="active")),
            FieldCondition(key="consolidated", match=MatchValue(value=True)),
        ]
        if user_id:
            conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))

        search_filter = Filter(must=conditions)

        results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=[0.0] * 1024,
            limit=10,
            score_threshold=0.0,
            raw_filter=search_filter,
        )

        # 过滤 saved_at 在 7 天内
        high_importance = []
        for r in results:
            payload = r.payload or {}
            saved_at = payload.get("saved_at", "")
            if saved_at and saved_at >= cutoff:
                high_importance.append(r)

        if len(high_importance) < 3:
            # 高重要性记忆不足，跳过 insight 生成
            logger.info("[SleepTime] Phase C: 高重要性记忆不足 3 条，跳过")
            return {"insights_created": 0}

        logger.info(f"[SleepTime] Phase C: 找到 {len(high_importance)} 条高重要性记忆，触发 reflect")

        # 触发 reflect
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.markdown_memory_service import markdown_memory_service

            async with AsyncSessionLocal() as db:
                result = await markdown_memory_service.reflect(db, user_id, days=7)
                return {"insights_created": result.get("created", 0)}

        except Exception as e:
            logger.warning(f"[SleepTime] Phase C reflect 失败: {e}")
            return {"insights_created": 0}

    async def _list_unconsolidated(self, user_id: int, days: int = 7,
                                   limit: int = 200) -> List[dict]:
        """列出未合并的记忆

        查找近 N 天内 consolidated != True 的 detail/summary。
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        conditions = [
            FieldCondition(key="decay_status", match=MatchValue(value="active")),
            # type in [detail, summary]
            FieldCondition(key="type", match=MatchAny(any=["detail", "summary"])),
        ]
        if user_id:
            conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))

        search_filter = Filter(must=conditions)

        results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=[0.0] * 1024,  # dummy vector, 靠 filter 筛选
            limit=limit * 2,
            score_threshold=0.0,
            raw_filter=search_filter,
        )

        items = []
        for r in results:
            payload = r.payload or {}
            # 过滤: consolidated != True 且 saved_at >= cutoff
            if payload.get("consolidated"):
                continue
            saved_at = payload.get("saved_at", "")
            if saved_at and saved_at >= cutoff:
                items.append({
                    "id": r.id,
                    "type": payload.get("type", ""),
                    "summary": payload.get("summary", ""),
                    "tags": payload.get("tags", []),
                    "importance": payload.get("importance", 5),
                    "saved_at": saved_at,
                })

        return items[:limit]
