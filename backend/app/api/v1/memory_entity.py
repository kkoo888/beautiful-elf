"""实体记忆 API — 借鉴 Hindsight TEMPR + CARA

端点:
  - /entities: 实体 CRUD
  - /entities/relations: 关系 CRUD
  - /entities/graph: 图谱数据（前端 React Flow 用）
  - /insights: 洞察 CRUD
  - /reflect: 触发反思（从近期记忆提取洞察）
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.memory_entity import MemoryEntity
from app.models.memory_entity_relation import MemoryEntityRelation
from app.models.memory_insight import MemoryInsight
from app.models.observation import MemoryObservation
from app.schemas.response import ApiResult, ApiPageResult, api_error

router = APIRouter()


# ═══════════════════════════════════════════════════
# 实体 CRUD
# ═══════════════════════════════════════════════════

@router.get("/entities", response_model=ApiPageResult)
async def list_entities(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
    entity_type: Optional[str] = Query(default=None, alias="entityType"),
    keyword: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """实体列表"""
    stmt = select(MemoryEntity).where(MemoryEntity.is_deleted == 0)
    count_stmt = select(func.count()).select_from(MemoryEntity).where(MemoryEntity.is_deleted == 0)

    if entity_type:
        stmt = stmt.where(MemoryEntity.entity_type == entity_type)
        count_stmt = count_stmt.where(MemoryEntity.entity_type == entity_type)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(MemoryEntity.name.like(like), MemoryEntity.aliases.like(like)))
        count_stmt = count_stmt.where(or_(MemoryEntity.name.like(like), MemoryEntity.aliases.like(like)))

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(MemoryEntity.mention_count.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    items = [_entity_to_dict(r) for r in rows]
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.post("/entities", response_model=ApiResult)
async def create_entity(
    name: str = Body(...),
    entity_type: str = Body(default="concept"),
    description: str = Body(default=""),
    aliases: str = Body(default=""),
    db: AsyncSession = Depends(get_db),
):
    """创建实体"""
    # 检查重名
    existing = (await db.execute(
        select(MemoryEntity).where(
            MemoryEntity.name == name, MemoryEntity.is_deleted == 0
        )
    )).scalar_one_or_none()
    if existing:
        return ApiResult(data=_entity_to_dict(existing))

    entity = MemoryEntity(
        name=name, entity_type=entity_type,
        description=description, aliases=aliases,
        mention_count=1, last_mentioned_at=datetime.now().isoformat(),
    )
    db.add(entity)
    await db.flush()
    await db.refresh(entity)
    return ApiResult(data=_entity_to_dict(entity))


@router.put("/entities/{entity_id}", response_model=ApiResult)
async def update_entity(
    entity_id: int,
    name: Optional[str] = Body(default=None),
    entity_type: Optional[str] = Body(default=None),
    description: Optional[str] = Body(default=None),
    aliases: Optional[str] = Body(default=None),
    db: AsyncSession = Depends(get_db),
):
    """更新实体"""
    entity = (await db.execute(
        select(MemoryEntity).where(MemoryEntity.id == entity_id, MemoryEntity.is_deleted == 0)
    )).scalar_one_or_none()
    if not entity:
        return api_error("NOT_FOUND", "实体不存在")

    if name is not None:
        entity.name = name
    if entity_type is not None:
        entity.entity_type = entity_type
    if description is not None:
        entity.description = description
    if aliases is not None:
        entity.aliases = aliases
    await db.flush()
    await db.refresh(entity)
    return ApiResult(data=_entity_to_dict(entity))


@router.delete("/entities/{entity_id}", response_model=ApiResult)
async def delete_entity(entity_id: int, db: AsyncSession = Depends(get_db)):
    """删除实体"""
    entity = (await db.execute(
        select(MemoryEntity).where(MemoryEntity.id == entity_id, MemoryEntity.is_deleted == 0)
    )).scalar_one_or_none()
    if not entity:
        return api_error("NOT_FOUND", "实体不存在")

    entity.is_deleted = 1
    await db.flush()
    return ApiResult(message="删除成功")


# ═══════════════════════════════════════════════════
# 关系 CRUD
# ═══════════════════════════════════════════════════

@router.get("/entities/relations", response_model=ApiResult)
async def list_relations(
    entity_id: Optional[int] = Query(default=None, alias="entityId"),
    db: AsyncSession = Depends(get_db),
):
    """查询关系（可按实体过滤）"""
    stmt = select(MemoryEntityRelation).where(MemoryEntityRelation.is_deleted == 0)
    if entity_id:
        stmt = stmt.where(or_(
            MemoryEntityRelation.source_entity_id == entity_id,
            MemoryEntityRelation.target_entity_id == entity_id,
        ))
    rows = (await db.execute(stmt)).scalars().all()
    return ApiResult(data=[_relation_to_dict(r) for r in rows])


@router.post("/entities/relations", response_model=ApiResult)
async def create_relation(
    source_entity_id: int = Body(...),
    target_entity_id: int = Body(...),
    relation_type: str = Body(default="related"),
    evidence: str = Body(default=""),
    source_obs_id: int = Body(default=0),
    db: AsyncSession = Depends(get_db),
):
    """创建关系"""
    if source_entity_id == target_entity_id:
        return api_error("INVALID", "不能自关联")

    # 检查是否已存在
    existing = (await db.execute(
        select(MemoryEntityRelation).where(
            MemoryEntityRelation.source_entity_id == source_entity_id,
            MemoryEntityRelation.target_entity_id == target_entity_id,
            MemoryEntityRelation.relation_type == relation_type,
            MemoryEntityRelation.is_deleted == 0,
        )
    )).scalar_one_or_none()

    if existing:
        existing.weight += 1
        if evidence:
            existing.evidence = evidence
        await db.flush()
        await db.refresh(existing)
        return ApiResult(data=_relation_to_dict(existing))

    rel = MemoryEntityRelation(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relation_type=relation_type,
        evidence=evidence,
        source_obs_id=source_obs_id,
        weight=1,
    )
    db.add(rel)
    await db.flush()
    await db.refresh(rel)
    return ApiResult(data=_relation_to_dict(rel))


@router.delete("/entities/relations/{relation_id}", response_model=ApiResult)
async def delete_relation(relation_id: int, db: AsyncSession = Depends(get_db)):
    """删除关系"""
    rel = (await db.execute(
        select(MemoryEntityRelation).where(
            MemoryEntityRelation.id == relation_id, MemoryEntityRelation.is_deleted == 0
        )
    )).scalar_one_or_none()
    if not rel:
        return api_error("NOT_FOUND", "关系不存在")
    rel.is_deleted = 1
    await db.flush()
    return ApiResult(message="删除成功")


# ═══════════════════════════════════════════════════
# 图谱数据（前端 React Flow 用）
# ═══════════════════════════════════════════════════

@router.get("/entities/graph", response_model=ApiResult)
async def get_entity_graph(
    db: AsyncSession = Depends(get_db),
):
    """获取实体图谱数据（nodes + edges）"""
    entities = (await db.execute(
        select(MemoryEntity).where(MemoryEntity.is_deleted == 0)
    )).scalars().all()

    relations = (await db.execute(
        select(MemoryEntityRelation).where(MemoryEntityRelation.is_deleted == 0)
    )).scalars().all()

    nodes = [{
        "id": f"entity-{e.id}",
        "name": e.name,
        "type": e.entity_type,
        "description": e.description,
        "mentionCount": e.mention_count,
    } for e in entities]

    edges = [{
        "id": f"rel-{r.id}",
        "source": f"entity-{r.source_entity_id}",
        "target": f"entity-{r.target_entity_id}",
        "type": r.relation_type,
        "weight": r.weight,
    } for r in relations]

    return ApiResult(data={"nodes": nodes, "edges": edges})


# ═══════════════════════════════════════════════════
# 洞察 CRUD
# ═══════════════════════════════════════════════════

@router.get("/insights", response_model=ApiPageResult)
async def list_insights(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200, alias="pageSize"),
    insight_type: Optional[str] = Query(default=None, alias="type"),
    status: str = Query(default="active"),
    db: AsyncSession = Depends(get_db),
):
    """洞察列表"""
    stmt = select(MemoryInsight).where(
        MemoryInsight.is_deleted == 0, MemoryInsight.status == status
    )
    count_stmt = select(func.count()).select_from(MemoryInsight).where(
        MemoryInsight.is_deleted == 0, MemoryInsight.status == status
    )
    if insight_type:
        stmt = stmt.where(MemoryInsight.insight_type == insight_type)
        count_stmt = count_stmt.where(MemoryInsight.insight_type == insight_type)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(MemoryInsight.confidence.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return ApiPageResult(data=[_insight_to_dict(r) for r in rows], total=total, page=page, page_size=page_size)


@router.post("/insights", response_model=ApiResult)
async def create_insight(
    content: str = Body(...),
    insight_type: str = Body(default="insight"),
    confidence: int = Body(default=50),
    source_period: str = Body(default=""),
    db: AsyncSession = Depends(get_db),
):
    """创建洞察"""
    insight = MemoryInsight(
        content=content, insight_type=insight_type,
        confidence=confidence, source_period=source_period,
        evidence_count=1, status="active",
    )
    db.add(insight)
    await db.flush()
    await db.refresh(insight)
    return ApiResult(data=_insight_to_dict(insight))


@router.put("/insights/{insight_id}", response_model=ApiResult)
async def update_insight(
    insight_id: int,
    content: Optional[str] = Body(default=None),
    confidence: Optional[int] = Body(default=None),
    status: Optional[str] = Body(default=None),
    db: AsyncSession = Depends(get_db),
):
    """更新洞察（强化/弱化置信度）"""
    insight = (await db.execute(
        select(MemoryInsight).where(MemoryInsight.id == insight_id, MemoryInsight.is_deleted == 0)
    )).scalar_one_or_none()
    if not insight:
        return api_error("NOT_FOUND", "洞察不存在")

    if content is not None:
        insight.content = content
    if confidence is not None:
        insight.confidence = max(0, min(100, confidence))
    if status is not None:
        insight.status = status
    await db.flush()
    await db.refresh(insight)
    return ApiResult(data=_insight_to_dict(insight))


@router.delete("/insights/{insight_id}", response_model=ApiResult)
async def delete_insight(insight_id: int, db: AsyncSession = Depends(get_db)):
    """删除洞察"""
    insight = (await db.execute(
        select(MemoryInsight).where(MemoryInsight.id == insight_id, MemoryInsight.is_deleted == 0)
    )).scalar_one_or_none()
    if not insight:
        return api_error("NOT_FOUND", "洞察不存在")
    insight.is_deleted = 1
    await db.flush()
    return ApiResult(message="删除成功")


# ═══════════════════════════════════════════════════
# Reflect — 触发反思（从近期记忆提取洞察）
# ═══════════════════════════════════════════════════

@router.post("/reflect", response_model=ApiResult)
async def trigger_reflect(
    days: int = Body(default=7),
    db: AsyncSession = Depends(get_db),
):
    """触发反思：从近期 observations 中提取模式和洞察

    这是一个简化版的 Reflect —— 实际生产中应调用 LLM。
    这里先做基础的统计分析。
    """
    # 获取近期 observations
    stmt = select(MemoryObservation).where(
        MemoryObservation.is_deleted == 0
    ).order_by(MemoryObservation.id.desc()).limit(50)
    observations = (await db.execute(stmt)).scalars().all()

    if not observations:
        return ApiResult(data={"insights": [], "message": "没有近期记忆可供分析"})

    # 统计分析
    category_counts = {}
    freshness_counts = {}
    for obs in observations:
        category_counts[obs.category] = category_counts.get(obs.category, 0) + 1
        freshness_counts[obs.freshness] = freshness_counts.get(obs.freshness, 0) + 1

    insights = []

    # 模式检测：某分类占比过高
    total = len(observations)
    for cat, count in category_counts.items():
        ratio = count / total
        if ratio > 0.5:
            cat_label = {"decisions": "决策", "pitfalls": "踩坑", "preferences": "偏好", "status": "状态"}.get(cat, cat)
            insight = MemoryInsight(
                content=f"近期 {ratio:.0%} 的记忆集中在「{cat_label}」领域，建议关注平衡。",
                insight_type="pattern",
                confidence=int(ratio * 100),
                source_period=f"最近 {total} 条记忆",
                evidence_count=count,
                status="active",
            )
            db.add(insight)
            insights.append(insight)

    # 趋势检测：weakening 记忆过多
    weakening = freshness_counts.get("weakening", 0) + freshness_counts.get("stale", 0)
    if weakening > total * 0.3:
        insight = MemoryInsight(
            content=f"有 {weakening} 条记忆正在衰减（weakening/stale），可能需要更新或归档。",
            insight_type="trend",
            confidence=70,
            source_period=f"最近 {total} 条记忆",
            evidence_count=weakening,
            status="active",
        )
        db.add(insight)
        insights.append(insight)

    # 风险检测：踩坑记忆较多
    pitfalls = category_counts.get("pitfalls", 0)
    if pitfalls > 3:
        insight = MemoryInsight(
            content=f"近期有 {pitfalls} 条踩坑记录，建议总结共性问题形成最佳实践。",
            insight_type="risk",
            confidence=60,
            source_period=f"最近 {total} 条记忆",
            evidence_count=pitfalls,
            status="active",
        )
        db.add(insight)
        insights.append(insight)

    await db.flush()

    return ApiResult(data={
        "insights": [_insight_to_dict(i) for i in insights],
        "analyzed": total,
        "categoryBreakdown": category_counts,
        "freshnessBreakdown": freshness_counts,
    })


# ═══════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════

def _entity_to_dict(e: MemoryEntity) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "entityType": e.entity_type,
        "description": e.description,
        "aliases": e.aliases,
        "mentionCount": e.mention_count,
        "lastMentionedAt": e.last_mentioned_at,
        "createdAt": str(e.created_at) if e.created_at else None,
    }


def _relation_to_dict(r: MemoryEntityRelation) -> dict:
    return {
        "id": r.id,
        "sourceEntityId": r.source_entity_id,
        "targetEntityId": r.target_entity_id,
        "relationType": r.relation_type,
        "weight": r.weight,
        "evidence": r.evidence,
        "sourceObsId": r.source_obs_id,
    }


def _insight_to_dict(i: MemoryInsight) -> dict:
    return {
        "id": i.id,
        "content": i.content,
        "insightType": i.insight_type,
        "confidence": i.confidence,
        "evidenceCount": i.evidence_count,
        "sourcePeriod": i.source_period,
        "status": i.status,
        "createdAt": str(i.created_at) if i.created_at else None,
    }
