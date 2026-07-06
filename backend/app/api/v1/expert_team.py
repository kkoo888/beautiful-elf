"""专家团工作流 API — 符合 API 设计规范"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.expert_team_service import ExpertTeamService
from app.schemas.expert_team import (
    ExpertTeamCreate, ExpertTeamUpdate, ExpertTeamOut, ExpertTeamBindExperts,
    ExpertCreate, ExpertUpdate, ExpertOut,
    ExpertTeamExecuteRequest,
    ExpertSkillCreate, ExpertSkillUpdate, ExpertSkillOut,
    ExpertTeamRunOut, ExpertRoleRunOut,
    PolishPromptRequest,
)
from app.schemas.response import ApiResult, ApiPageResult
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
service = ExpertTeamService()


# ─── 工具接口 ──────────────────────────────────────────────

@router.post("/polish-prompt", response_model=ApiResult[str])
async def polish_prompt(
    data: PolishPromptRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[str]:
    """润色提示词 — 调用默认大模型优化"""
    result = await service.polish_prompt(db, data)
    return ApiResult(data=result)


# ─── 专家 CRUD（独立实体）─────────────────────────────────

@router.get("/experts", response_model=ApiPageResult[ExpertOut])
async def list_experts(
    enabled: Optional[int] = Query(default=None, ge=0, le=1, description="启用状态"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ExpertOut]:
    """获取专家列表"""
    items, total = await service.list_experts(
        db, page=pagination.page, page_size=pagination.page_size, enabled=enabled,
    )
    return ApiPageResult(data=items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.post("/experts", response_model=ApiResult[ExpertOut])
async def create_expert(
    data: ExpertCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertOut]:
    """创建专家"""
    expert = await service.create_expert(db, data)
    return ApiResult(data=expert)


@router.get("/experts/{expert_id}", response_model=ApiResult[ExpertOut])
async def get_expert(
    expert_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertOut]:
    """获取专家详情"""
    expert = await service.get_expert_by_id(db, expert_id)
    return ApiResult(data=expert)


@router.put("/experts/{expert_id}", response_model=ApiResult[ExpertOut])
async def update_expert(
    expert_id: int,
    data: ExpertUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertOut]:
    """更新专家"""
    expert = await service.update_expert(db, expert_id, data)
    return ApiResult(data=expert)


@router.delete("/experts/{expert_id}", response_model=ApiResult)
async def delete_expert(
    expert_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除专家"""
    await service.delete_expert(db, expert_id)
    return ApiResult(message="删除成功")


# ─── 专家技能绑定 ─────────────────────────────────────────

@router.get("/experts/{expert_id}/skills", response_model=ApiResult)
async def list_expert_skills(
    expert_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """查询专家绑定的技能列表"""
    skills = await service.list_expert_skills(db, expert_id)
    return ApiResult(data=skills)


@router.post("/experts/{expert_id}/skills", response_model=ApiResult[ExpertSkillOut])
async def bind_skill_to_expert(
    expert_id: int,
    data: ExpertSkillCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertSkillOut]:
    """绑定技能到专家"""
    bind = await service.bind_skill(db, expert_id, data)
    return ApiResult(data=bind)


@router.put("/expert-skills/{bind_id}", response_model=ApiResult[ExpertSkillOut])
async def update_expert_skill_bind(
    bind_id: int,
    data: ExpertSkillUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertSkillOut]:
    """更新专家技能绑定"""
    bind = await service.update_skill_bind(db, bind_id, data)
    return ApiResult(data=bind)


@router.delete("/expert-skills/{bind_id}", response_model=ApiResult)
async def unbind_expert_skill(
    bind_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """解绑专家技能"""
    await service.unbind_skill(db, bind_id)
    return ApiResult(message="解绑成功")


# ─── 专家知识源 ──────────────────────────────────────────

@router.post("/experts/{expert_id}/knowledge")
async def add_expert_knowledge(
    expert_id: int,
    data: dict,
):
    """添加知识到专家知识库

    Body: {"content": "知识内容", "source": "来源标识"}
    """
    content = data.get("content", "")
    source = data.get("source", "")
    if not content:
        return ApiResult(code=400, message="content 不能为空")

    from app.agent.expert_team.knowledge import KNOWLEDGE_COLLECTION
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.core.embeddings import get_embeddings
    import uuid

    qdrant = QdrantMapper()
    qdrant.ensure_collection(KNOWLEDGE_COLLECTION)
    qdrant.ensure_payload_index(KNOWLEDGE_COLLECTION, "expert_id", "keyword")

    embeddings = get_embeddings()
    vector = await embeddings.aembed_query(content)

    point_id = str(uuid.uuid4())
    qdrant.upsert(
        collection=KNOWLEDGE_COLLECTION,
        point_id=point_id,
        vector=vector,
        payload={
            "content": content,
            "source": source,
            "expert_id": str(expert_id),
        },
    )
    return ApiResult(data={"id": point_id, "message": "知识已添加"})


@router.get("/experts/{expert_id}/knowledge")
async def list_expert_knowledge(
    expert_id: int,
):
    """查询专家知识库"""
    from app.agent.expert_team.knowledge import KNOWLEDGE_COLLECTION
    from app.mappers.qdrant_mapper import QdrantMapper

    qdrant = QdrantMapper()
    info = qdrant.collection_info(KNOWLEDGE_COLLECTION)
    if not info:
        return ApiResult(data=[])

    results, _ = qdrant.scroll(
        collection=KNOWLEDGE_COLLECTION,
        filter_payload={"expert_id": str(expert_id)},
        limit=50,
    )
    items = [{"id": r["id"], **(r.get("payload") or {})} for r in results]
    return ApiResult(data=items)


@router.delete("/knowledge/{point_id}")
async def delete_expert_knowledge(
    point_id: str,
):
    """删除专家知识"""
    from app.agent.expert_team.knowledge import KNOWLEDGE_COLLECTION
    from app.mappers.qdrant_mapper import QdrantMapper

    qdrant = QdrantMapper()
    try:
        qdrant._client.delete(
            collection_name=KNOWLEDGE_COLLECTION,
            points_selector=[point_id],
        )
    except Exception as e:
        logger.warning(f"删除知识失败: {e}")
        return ApiResult(code=500, message=f"删除失败: {e}")
    return ApiResult(message="删除成功")


# ─── 运行记录（具体路由在前，通配在后）───────────────────

@router.get("/runs/all", response_model=ApiPageResult[ExpertTeamRunOut])
async def list_all_expert_runs(
    status: Optional[int] = Query(default=None, description="状态筛选"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ExpertTeamRunOut]:
    """获取所有专家团运行记录"""
    items, total = await service.list_all_runs(
        db, page=pagination.page, page_size=pagination.page_size, status=status,
    )
    return ApiPageResult(data=items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.get("/runs/{run_id}", response_model=ApiResult[ExpertTeamRunOut])
async def get_expert_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertTeamRunOut]:
    """获取运行记录详情"""
    run = await service.get_run_by_id(db, run_id)
    return ApiResult(data=run)


# ─── 专家团 CRUD ─────────────────────────────────────────

@router.get("", response_model=ApiPageResult[ExpertTeamOut])
async def list_expert_teams(
    category: Optional[str] = Query(default=None, description="分类筛选"),
    enabled: Optional[int] = Query(default=None, ge=0, le=1, description="启用状态"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ExpertTeamOut]:
    """获取专家团列表"""
    items, total = await service.list_teams(
        db, page=pagination.page, page_size=pagination.page_size,
        category=category, enabled=enabled,
    )
    return ApiPageResult(data=items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.post("", response_model=ApiResult[ExpertTeamOut])
async def create_expert_team(
    data: ExpertTeamCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertTeamOut]:
    """创建专家团（可绑定已有专家）"""
    team = await service.create_team(db, data)
    return ApiResult(data=team)


@router.get("/{team_id}", response_model=ApiResult[ExpertTeamOut])
async def get_expert_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertTeamOut]:
    """获取专家团详情"""
    team = await service.get_team_by_id(db, team_id)
    return ApiResult(data=team)


@router.put("/{team_id}", response_model=ApiResult[ExpertTeamOut])
async def update_expert_team(
    team_id: int,
    data: ExpertTeamUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertTeamOut]:
    """更新专家团"""
    team = await service.update_team(db, team_id, data)
    return ApiResult(data=team)


@router.delete("/{team_id}", response_model=ApiResult)
async def delete_expert_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除专家团"""
    await service.delete_team(db, team_id)
    return ApiResult(message="删除成功")


# ─── 专家团绑定专家 ──────────────────────────────────────

@router.post("/{team_id}/bind-experts", response_model=ApiResult[ExpertTeamOut])
async def bind_experts_to_team(
    team_id: int,
    data: ExpertTeamBindExperts,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertTeamOut]:
    """绑定专家到专家团（整体替换）"""
    team = await service.bind_experts(db, team_id, data)
    return ApiResult(data=team)


# ─── 执行与运行记录 ─────────────────────────────────────

@router.get("/{team_id}/runs", response_model=ApiPageResult[ExpertTeamRunOut])
async def list_expert_team_runs(
    team_id: int,
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ExpertTeamRunOut]:
    """获取专家团运行记录"""
    items, total = await service.list_runs_by_team(
        db, team_id, page=pagination.page, page_size=pagination.page_size,
    )
    return ApiPageResult(data=items, total=total, page=pagination.page, page_size=pagination.page_size)


# ─── 人类审核 ──────────────────────────────────────────

@router.post("/runs/{run_id}/review")
async def review_expert_run(
    run_id: int,
    data: dict,
):
    """人类审核 — 审批/拒绝/修改专家团执行

    Body: {"action": "approve|reject|modify", "feedback": "审核意见", "modifications": {}}
    """
    from app.agent.expert_team.checkpoint import resume_from_review, HumanReviewRequest

    review = HumanReviewRequest(
        run_id=run_id,
        action=data.get("action", "approve"),
        feedback=data.get("feedback", ""),
        modifications=data.get("modifications", {}),
    )

    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        success = await resume_from_review(db, run_id, review)

    if success:
        return ApiResult(data={"status": "resumed", "message": "已恢复执行"})
    else:
        return ApiResult(data={"status": "stopped", "message": "已停止执行"})


@router.get("/runs/{run_id}/checkpoints")
async def get_run_checkpoints(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取运行检查点列表（执行回放）"""
    from app.repository.expert_team_repo import ExpertTeamRepository
    repo = ExpertTeamRepository()
    run = await repo.find_run_by_id(db, run_id)
    if not run:
        return ApiResult(code=404, message="运行记录不存在")

    progress = run.progress_json or []
    if isinstance(progress, str):
        try:
            progress = json.loads(progress)
        except (json.JSONDecodeError, TypeError):
            progress = []

    return ApiResult(data=progress)


# ─── 角色执行记录 ───────────────────────────────────────

@router.get("/runs/{run_id}/role-runs", response_model=ApiResult)
async def list_role_runs(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """查询某次运行的所有角色执行记录"""
    runs = await service.list_role_runs(db, run_id)
    return ApiResult(data=runs)

