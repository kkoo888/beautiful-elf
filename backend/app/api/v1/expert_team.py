"""专家团工作流 API — 符合 API 设计规范"""
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

@router.post("/{team_id}/execute", response_model=ApiResult)
async def execute_expert_team(
    team_id: int,
    data: ExpertTeamExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """执行专家团工作流"""
    result = await service.execute_team(db, team_id, data)
    return ApiResult(data=result)


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


# ─── 角色执行记录 ───────────────────────────────────────

@router.get("/runs/{run_id}/role-runs", response_model=ApiResult)
async def list_role_runs(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """查询某次运行的所有角色执行记录"""
    runs = await service.list_role_runs(db, run_id)
    return ApiResult(data=runs)
