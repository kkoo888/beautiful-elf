"""实体记忆 API — 借鉴 Hindsight TEMPR + CARA

端点:
  - /entities: 实体 CRUD
  - /entities/relations: 关系 CRUD
  - /entities/graph: 图谱数据（前端 React Flow 用）
  - /insights: 洞察 CRUD
  - /insights/{id}/history: Insight 演化历史
  - /insights/conflicts: 矛盾 Insight 列表
  - /reflect: 触发反思（从近期记忆提取洞察）
  - /episodes: 经历列表
  - /episodes/{id}: 经历详情
  - /episodes/by-entity/{entity_id}: 按实体查经历
  - /episodes/search: 经历语义检索
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
# Reflect — LLM 深度反思（借鉴 Hindsight CARA）
# ═══════════════════════════════════════════════════

@router.post("/reflect", response_model=ApiResult)
async def trigger_reflect(
    days: int = Body(default=7),
    db: AsyncSession = Depends(get_db),
):
    """触发深度反思 — LLM 驱动，从近期 Observations 提取深度洞察

    借鉴 Hindsight CARA Reflect:
      - 输入近期提炼记忆 + 已有洞察
      - LLM 分析跨时间模式、矛盾、趋势、风险
      - 产生语义深度洞察（非模板化）
    """
    from app.services.markdown_memory_service import markdown_memory_service
    try:
        result = await markdown_memory_service.reflect(db, user_id=0, days=days)
    except ValueError as e:
        return api_error("MEMORY_REFLECT_FAILED", str(e))
    return ApiResult(data=result)


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


# ═══════════════════════════════════════════════════
# Agent 行为画像（借鉴 Hindsight CARA Disposition Profile）
# ═══════════════════════════════════════════════════

from app.models.agent_profile import AgentProfile


@router.get("/profile", response_model=ApiResult)
async def get_active_profile(
    db: AsyncSession = Depends(get_db),
):
    """获取当前活跃的 Agent 行为画像"""
    profile = (await db.execute(
        select(AgentProfile).where(
            AgentProfile.is_deleted == 0, AgentProfile.is_active == 1
        ).limit(1)
    )).scalar_one_or_none()

    if not profile:
        # 返回默认画像
        return ApiResult(data=_profile_to_dict_default())
    return ApiResult(data=_profile_to_dict(profile))


@router.post("/profile", response_model=ApiResult)
async def create_or_update_profile(
    name: str = Body(default="default"),
    background: str = Body(default=""),
    skepticism: int = Body(default=2, ge=1, le=5),
    literalism: int = Body(default=3, ge=1, le=5),
    empathy: int = Body(default=4, ge=1, le=5),
    bias_strength: float = Body(default=0.5, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """创建或更新 Agent 行为画像"""
    existing = (await db.execute(
        select(AgentProfile).where(
            AgentProfile.is_deleted == 0, AgentProfile.is_active == 1
        ).limit(1)
    )).scalar_one_or_none()

    if existing:
        existing.name = name
        existing.background = background
        existing.skepticism = skepticism
        existing.literalism = literalism
        existing.empathy = empathy
        existing.bias_strength = bias_strength
        await db.flush()
        await db.refresh(existing)
        return ApiResult(data=_profile_to_dict(existing))

    profile = AgentProfile(
        name=name, background=background,
        skepticism=skepticism, literalism=literalism,
        empathy=empathy, bias_strength=bias_strength,
        is_active=1,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return ApiResult(data=_profile_to_dict(profile))


def _profile_to_dict(p: AgentProfile) -> dict:
    """AgentProfile ORM → dict（camelCase）"""
    return {
        "id": p.id,
        "name": p.name,
        "background": p.background,
        "skepticism": p.skepticism,
        "literalism": p.literalism,
        "empathy": p.empathy,
        "biasStrength": p.bias_strength,
        "isActive": bool(p.is_active),
        "createdAt": str(p.created_at) if p.created_at else None,
    }


def _profile_to_dict_default() -> dict:
    """默认行为画像"""
    return {
        "id": 0,
        "name": "default",
        "background": "",
        "skepticism": 2,
        "literalism": 3,
        "empathy": 4,
        "biasStrength": 0.5,
        "isActive": False,
        "createdAt": None,
    }


# ═══════════════════════════════════════════════════
# v5.0: 经历对话分组（借鉴 Zep Graphiti）
# ═══════════════════════════════════════════════════

from app.models.memory_episode import MemoryEpisode
from app.repository.episode_repo import EpisodeRepository


@router.get("/episodes", response_model=ApiPageResult)
async def list_episodes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
):
    """经历列表（分页）"""
    repo = EpisodeRepository()
    items = await repo.find_all(db, user_id=0, offset=(page - 1) * page_size, limit=page_size)
    total = await repo.count(db, user_id=0)
    return ApiPageResult(
        data=[_episode_to_dict(e) for e in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/episodes/{episode_id}", response_model=ApiResult)
async def get_episode(
    episode_id: int,
    db: AsyncSession = Depends(get_db),
):
    """经历详情"""
    repo = EpisodeRepository()
    episode = await repo.find_by_id(db, episode_id)
    if not episode:
        return api_error("NOT_FOUND", "经历不存在")
    return ApiResult(data=_episode_to_dict(episode))


@router.get("/episodes/by-entity/{entity_id}", response_model=ApiResult)
async def get_episodes_by_entity(
    entity_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """按实体 ID 查找关联经历"""
    repo = EpisodeRepository()
    episodes = await repo.find_by_entity(db, entity_id, limit=limit)
    return ApiResult(data=[_episode_to_dict(e) for e in episodes])


@router.get("/episodes/search", response_model=ApiResult)
async def search_episodes(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """经历语义检索（通过 Qdrant）"""
    # 简单的 LIKE 查询实现（语义检索需要 embedding + Qdrant）
    def _escape_like(s: str) -> str:
        return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    
    like = f"%{_escape_like(q)}%"
    stmt = select(MemoryEpisode).where(
        MemoryEpisode.is_deleted == 0,
        or_(MemoryEpisode.title.like(like), MemoryEpisode.summary.like(like)),
    ).order_by(MemoryEpisode.started_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return ApiResult(data=[_episode_to_dict(e) for e in rows])


def _episode_to_dict(e: MemoryEpisode) -> dict:
    return {
        "id": e.id,
        "userId": e.user_id,
        "conversationId": e.conversation_id,
        "title": e.title,
        "summary": e.summary,
        "startedAt": str(e.started_at) if e.started_at else None,
        "endedAt": str(e.ended_at) if e.ended_at else None,
        "messageCount": e.message_count,
        "entityIds": e.entity_ids,
        "observationIds": e.observation_ids,
        "tags": e.tags,
        "qdrantPointId": e.qdrant_point_id,
        "createdAt": str(e.created_at) if e.created_at else None,
        "updatedAt": str(e.updated_at) if e.updated_at else None,
    }


# ═══════════════════════════════════════════════════
# v5.0: Insight 演化历史 + 冲突查询
# ═══════════════════════════════════════════════════

from app.services.insight_arbitration_service import InsightArbitrationService


@router.get("/insights/{insight_id}/history", response_model=ApiResult)
async def get_insight_history(
    insight_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Insight 演化历史（审计追踪）"""
    arbiter = InsightArbitrationService()
    history = await arbiter.get_insight_history(db, insight_id, limit=limit)
    return ApiResult(data=history)


@router.get("/insights/conflicts", response_model=ApiResult)
async def get_insight_conflicts(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """矛盾 Insight 列表"""
    arbiter = InsightArbitrationService()
    conflicts = await arbiter.get_conflicts(db, user_id=0, limit=limit)
    return ApiResult(data=conflicts)
