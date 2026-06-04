"""专家团工作流 API — 符合 API 设计规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.expert_team_service import ExpertTeamService
from app.schemas.expert_team import (
    ExpertTeamCreate, ExpertTeamUpdate, ExpertTeamOut,
    ExpertMemberCreate, ExpertMemberUpdate,
    ExpertTeamExecuteRequest,
    RoleSkillCreate, RoleSkillUpdate, RoleSkillOut,
    ExpertTeamRunOut, ExpertRoleRunOut,
)
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
service = ExpertTeamService()


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
    """创建专家团（含成员）"""
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


# ─── 专家成员 ───────────────────────────────────────────

@router.post("/{team_id}/members", response_model=ApiResult[ExpertMemberOut])
async def add_expert_member(
    team_id: int,
    data: ExpertMemberCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertMemberOut]:
    """添加专家成员"""
    member = await service.add_member(db, team_id, data)
    return ApiResult(data=member)


@router.put("/members/{member_id}", response_model=ApiResult[ExpertMemberOut])
async def update_expert_member(
    member_id: int,
    data: ExpertMemberUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ExpertMemberOut]:
    """更新专家成员"""
    update_data = data.model_dump(exclude_unset=True, by_alias=False)
    member = await service.update_member(db, member_id, update_data)
    return ApiResult(data=member)


@router.delete("/members/{member_id}", response_model=ApiResult)
async def delete_expert_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除专家成员"""
    await service.delete_member(db, member_id)
    return ApiResult(message="删除成功")


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


# ─── 角色技能绑定 ───────────────────────────────────────

@router.get("/members/{member_id}/skills", response_model=ApiResult)
async def list_member_skills(
    member_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """查询成员绑定的技能列表"""
    skills = await service.list_member_skills(db, member_id)
    return ApiResult(data=skills)


@router.post("/members/{member_id}/skills", response_model=ApiResult[RoleSkillOut])
async def bind_skill_to_member(
    member_id: int,
    data: RoleSkillCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[RoleSkillOut]:
    """绑定技能到成员"""
    bind = await service.bind_skill(db, member_id, data)
    return ApiResult(data=bind)


@router.put("/skills/{bind_id}", response_model=ApiResult[RoleSkillOut])
async def update_skill_bind(
    bind_id: int,
    data: RoleSkillUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[RoleSkillOut]:
    """更新角色技能绑定"""
    bind = await service.update_skill_bind(db, bind_id, data)
    return ApiResult(data=bind)


@router.delete("/skills/{bind_id}", response_model=ApiResult)
async def unbind_skill(
    bind_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """解绑技能"""
    await service.unbind_skill(db, bind_id)
    return ApiResult(message="解绑成功")


# ─── 角色执行记录 ───────────────────────────────────────

@router.get("/runs/{run_id}/role-runs", response_model=ApiResult)
async def list_role_runs(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """查询某次运行的所有角色执行记录"""
    runs = await service.list_role_runs(db, run_id)
    return ApiResult(data=runs)
