"""专家团记忆系统 — 经验存储 + 原子事实提取 + 合并去重

核心思想：
  1. 执行完成后，LLM 从专家输出中提取原子事实
  2. embedding → 存入 Qdrant expert_experience collection
  3. 下次执行前，根据子任务语义检索相关经验注入 prompt
  4. 存储时自动检查相似度 > 0.85 → LLM 判断 keep/update/delete
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)

EXPERIENCE_COLLECTION = "expert_experience"


class AtomicFact(BaseModel):
    """原子事实"""
    content: str = Field(..., description="事实内容（一句话）")
    category: str = Field(default="general", description="分类: decision/insight/pattern/risk/tool")
    importance: float = Field(default=0.5, ge=0, le=1, description="重要性 0-1")


class FactExtraction(BaseModel):
    """事实提取结果"""
    facts: list[AtomicFact] = Field(default_factory=list, description="提取的原子事实")


class ConsolidationDecision(BaseModel):
    """合并决策"""
    action: str = Field(..., description="keep/update/delete/insert_new")
    updated_content: str = Field(default="", description="更新后的内容（action=update 时）")
    reason: str = Field(default="", description="决策原因")


async def extract_facts(
    db,
    provider_id: int,
    model_name: str,
    expert_name: str,
    expert_role: str,
    subtask: str,
    output: str,
    temperature: float = 0.3,
) -> list[AtomicFact]:
    """从专家输出中提取原子事实

    Args:
        expert_name: 专家名称
        expert_role: 专家角色
        subtask: 子任务
        output: 专家输出内容
    """
    from app.agent.llm_service import llm_service

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        extraction_prompt = f"""请从以下专家输出中提取值得记住的原子事实。

## 专家: {expert_name} ({expert_role})
## 子任务: {subtask}

## 专家输出
{output[:3000]}

提取规则：
1. 每个事实是一个独立的、可检索的陈述句
2. 提取决策、洞察、模式、风险、工具推荐等有价值的信息
3. 跳过通用描述和过渡句
4. 最多提取 10 个事实
5. 为每个事实标注分类和重要性"""

        structured_llm = llm.with_structured_output(FactExtraction)
        result = await structured_llm.ainvoke(extraction_prompt)
        return result.facts[:10]

    except Exception as e:
        logger.warning(f"事实提取失败: {e}")
        return []


async def store_experience(
    expert_id: int,
    team_id: int,
    facts: list[AtomicFact],
    embedding_model: str = "text-embedding-3-small",
    db=None,
) -> int:
    """存储经验到 Qdrant expert_experience collection

    自动合并去重：相似度 > 0.85 时由 LLM 决定 keep/update/delete。

    Returns:
        存储的事实数量
    """
    if not facts:
        return 0

    try:
        from app.mappers.qdrant_mapper import QdrantMapper
        from app.core.embeddings import get_embeddings
        import uuid

        qdrant = QdrantMapper()
        qdrant.ensure_collection(EXPERIENCE_COLLECTION)
        qdrant.ensure_payload_index(EXPERIENCE_COLLECTION, "expert_id", "keyword")
        qdrant.ensure_payload_index(EXPERIENCE_COLLECTION, "team_id", "keyword")
        qdrant.ensure_payload_index(EXPERIENCE_COLLECTION, "category", "keyword")

        embeddings = get_embeddings()
        stored = 0

        for fact in facts:
            # 生成 embedding
            vector = await embeddings.aembed_query(fact.content)

            # 检查是否有相似记忆（合并去重）
            similar = qdrant.search(
                collection=EXPERIENCE_COLLECTION,
                query_vector=vector,
                limit=1,
                score_threshold=0.85,
                filter_payload={"expert_id": str(expert_id)},
            )

            if similar:
                # 有相似记忆，决定合并策略
                existing = similar[0]
                existing_content = (existing.payload or {}).get("content", "")
                decision = await _consolidate(existing_content, fact.content, db=db)
                if decision.action == "keep":
                    continue  # 旧的还准，跳过
                elif decision.action == "update":
                    # 更新旧记忆
                    new_vector = await embeddings.aembed_query(decision.updated_content)
                    qdrant.upsert(
                        collection=EXPERIENCE_COLLECTION,
                        point_id=str(existing.id),
                        vector=new_vector,
                        payload={
                            "content": decision.updated_content,
                            "expert_id": str(expert_id),
                            "team_id": str(team_id),
                            "category": fact.category,
                            "importance": fact.importance,
                            "updated_at": _now_iso(),
                        },
                    )
                    stored += 1
                    continue
                elif decision.action == "delete":
                    # 删除旧记忆，插入新的
                    pass  # 继续到下面的 upsert

            # 插入新记忆
            point_id = str(uuid.uuid4())
            qdrant.upsert(
                collection=EXPERIENCE_COLLECTION,
                point_id=point_id,
                vector=vector,
                payload={
                    "content": fact.content,
                    "expert_id": str(expert_id),
                    "team_id": str(team_id),
                    "category": fact.category,
                    "importance": fact.importance,
                    "created_at": _now_iso(),
                },
            )
            stored += 1

        return stored

    except Exception as e:
        logger.warning(f"经验存储失败: {e}")
        return 0


async def recall_experience(
    expert_id: int,
    subtask: str,
    embedding_model: str = "text-embedding-3-small",
    top_k: int = 5,
    half_life_days: int = 14,
) -> str:
    """召回相关经验

    复合评分：semantic × 0.4 + recency × 0.3 + importance × 0.3

    Returns:
        格式化的经验文本，无经验时返回空字符串
    """
    try:
        from app.mappers.qdrant_mapper import QdrantMapper
        from app.core.embeddings import get_embeddings
        from datetime import datetime, timezone

        qdrant = QdrantMapper()
        info = qdrant.collection_info(EXPERIENCE_COLLECTION)
        if not info or info.get("points_count", 0) == 0:
            return ""

        embeddings = get_embeddings()
        query_vector = await embeddings.aembed_query(subtask)

        results = qdrant.search(
            collection=EXPERIENCE_COLLECTION,
            query_vector=query_vector,
            limit=top_k * 2,  # 多取一些，后面重排序
            score_threshold=0.2,
            filter_payload={"expert_id": str(expert_id)},
        )

        if not results:
            return ""

        # 复合评分重排序
        now = datetime.now(timezone.utc)
        scored = []
        for r in results:
            payload = r.payload or {}
            semantic = r.score
            importance = payload.get("importance", 0.5)

            # 时间衰减
            created_at = payload.get("created_at", "")
            recency = 0.5
            if created_at:
                try:
                    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    age_days = (now - created).total_seconds() / 86400
                    recency = 0.5 ** (age_days / half_life_days)
                except (ValueError, TypeError):
                    pass

            composite = 0.4 * semantic + 0.3 * recency + 0.3 * importance
            scored.append((composite, payload))

        scored.sort(key=lambda x: x[0], reverse=True)

        chunks = []
        for _, payload in scored[:top_k]:
            content = payload.get("content", "")
            category = payload.get("category", "")
            prefix = f"[{category}] " if category else ""
            chunks.append(f"{prefix}{content}")

        if not chunks:
            return ""

        return "\n\n## 相关经验\n" + "\n".join(f"- {c}" for c in chunks)

    except Exception as e:
        logger.warning(f"经验召回失败: {e}")
        return ""


async def _consolidate(existing: str, new: str, db=None) -> ConsolidationDecision:
    """记忆合并决策"""
    from app.agent.llm_service import llm_service

    try:
        llm = await llm_service.get_chat_llm(db, temperature=0.2)
        prompt = f"""以下是两条相似的记忆，请决定如何处理。

## 已有记忆
{existing}

## 新记忆
{new}

选项：
- keep: 已有记忆准确，不需要更新
- update: 两条都有价值，合并为一条更完整的
- delete: 已有记忆过时，用新的替换
- insert_new: 两条是不同方面，都保留

请输出决策。"""

        structured_llm = llm.with_structured_output(ConsolidationDecision)
        return await structured_llm.ainvoke(prompt)

    except Exception:
        return ConsolidationDecision(action="insert_new", reason="合并判断失败，默认保留两条")


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
