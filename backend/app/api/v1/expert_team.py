"""专家团工作流 API — 符合 API 设计规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.core.exceptions import RecordNotFoundError
from app.services.expert_team_service import ExpertTeamService
from app.schemas.expert_team import (
    ExpertTeamCreate, ExpertTeamUpdate, ExpertTeamOut,
    ExpertMemberCreate, ExpertMemberUpdate,
    ExpertTeamExecuteRequest,
    RoleSkillCreate, RoleSkillUpdate,
)
from app.schemas.response import ok, ok_page, fail

router = APIRouter()
service = ExpertTeamService()


def _req_id(request: Request) -> str:
    """从请求中获取 request_id，无则生成"""
    return getattr(request.state, "request_id", "")


# ─── 运行记录（具体路由在前，通配在后）───────────────────

@router.get("/runs/all")
async def list_all_expert_runs(
    request: Request,
    status: Optional[int] = Query(default=None, description="状态筛选"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    """获取所有专家团运行记录"""
    items, total = await service.list_all_runs(
        db, page=pagination.page, page_size=pagination.page_size, status=status,
    )
    return ok_page(data=items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.get("/runs/{run_id}")
async def get_expert_run(
    request: Request,
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取运行记录详情"""
    try:
        run = await service.get_run_by_id(db, run_id)
        return ok(data=run)
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查运行记录 ID", _req_id(request))


# ─── 专家团 CRUD ─────────────────────────────────────────

@router.get("")
async def list_expert_teams(
    request: Request,
    category: Optional[str] = Query(default=None, description="分类筛选"),
    enabled: Optional[int] = Query(default=None, ge=0, le=1, description="启用状态"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    """获取专家团列表"""
    items, total = await service.list_teams(
        db, page=pagination.page, page_size=pagination.page_size,
        category=category, enabled=enabled,
    )
    return ok_page(data=items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.post("")
async def create_expert_team(
    request: Request,
    data: ExpertTeamCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建专家团（含成员）"""
    team = await service.create_team(db, data)
    return ok(data=team)


@router.get("/{team_id}")
async def get_expert_team(
    request: Request,
    team_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取专家团详情"""
    try:
        team = await service.get_team_by_id(db, team_id)
        return ok(data=team)
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查专家团 ID", _req_id(request))


@router.put("/{team_id}")
async def update_expert_team(
    request: Request,
    team_id: int,
    data: ExpertTeamUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新专家团"""
    try:
        team = await service.update_team(db, team_id, data)
        return ok(data=team)
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查专家团 ID", _req_id(request))


@router.delete("/{team_id}")
async def delete_expert_team(
    request: Request,
    team_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除专家团"""
    try:
        await service.delete_team(db, team_id)
        return ok(data=None, message="删除成功")
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查专家团 ID", _req_id(request))


# ─── 专家成员 ───────────────────────────────────────────

@router.post("/{team_id}/members")
async def add_expert_member(
    request: Request,
    team_id: int,
    data: ExpertMemberCreate,
    db: AsyncSession = Depends(get_db),
):
    """添加专家成员"""
    try:
        member = await service.add_member(db, team_id, data)
        return ok(data=member)
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查专家团 ID", _req_id(request))


@router.put("/members/{member_id}")
async def update_expert_member(
    request: Request,
    member_id: int,
    data: ExpertMemberUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新专家成员"""
    try:
        update_data = data.model_dump(exclude_unset=True, by_alias=False)
        member = await service.update_member(db, member_id, update_data)
        return ok(data=member)
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查成员 ID", _req_id(request))


@router.delete("/members/{member_id}")
async def delete_expert_member(
    request: Request,
    member_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除专家成员"""
    try:
        await service.delete_member(db, member_id)
        return ok(data=None, message="删除成功")
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查成员 ID", _req_id(request))


# ─── 执行与运行记录 ─────────────────────────────────────

@router.post("/{team_id}/execute")
async def execute_expert_team(
    request: Request,
    team_id: int,
    data: ExpertTeamExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """执行专家团工作流"""
    try:
        result = await service.execute_team(db, team_id, data)
        return ok(data=result)
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查专家团 ID", _req_id(request))
    except Exception as e:
        return fail("AI_INTERNAL_ERROR", f"执行失败: {str(e)}", "请稍后重试", _req_id(request))


@router.get("/{team_id}/runs")
async def list_expert_team_runs(
    request: Request,
    team_id: int,
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    """获取专家团运行记录"""
    items, total = await service.list_runs_by_team(
        db, team_id, page=pagination.page, page_size=pagination.page_size,
    )
    return ok_page(data=items, total=total, page=pagination.page, page_size=pagination.page_size)


# ─── 角色技能绑定 ───────────────────────────────────────

@router.get("/members/{member_id}/skills")
async def list_member_skills(
    request: Request,
    member_id: int,
    db: AsyncSession = Depends(get_db),
):
    """查询成员绑定的技能列表"""
    try:
        skills = await service.list_member_skills(db, member_id)
        return ok(data=skills)
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查成员 ID", _req_id(request))


@router.post("/members/{member_id}/skills")
async def bind_skill_to_member(
    request: Request,
    member_id: int,
    data: RoleSkillCreate,
    db: AsyncSession = Depends(get_db),
):
    """绑定技能到成员"""
    try:
        bind = await service.bind_skill(db, member_id, data)
        return ok(data=bind)
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查成员或技能 ID", _req_id(request))


@router.put("/skills/{bind_id}")
async def update_skill_bind(
    request: Request,
    bind_id: int,
    data: RoleSkillUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新角色技能绑定"""
    try:
        bind = await service.update_skill_bind(db, bind_id, data)
        return ok(data=bind)
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查绑定 ID", _req_id(request))


@router.delete("/skills/{bind_id}")
async def unbind_skill(
    request: Request,
    bind_id: int,
    db: AsyncSession = Depends(get_db),
):
    """解绑技能"""
    try:
        await service.unbind_skill(db, bind_id)
        return ok(data=None, message="解绑成功")
    except RecordNotFoundError as e:
        return fail("EXPERT_TEAM_NOT_FOUND", str(e), "请检查绑定 ID", _req_id(request))


# ─── 角色执行记录 ───────────────────────────────────────

@router.get("/runs/{run_id}/role-runs")
async def list_role_runs(
    request: Request,
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """查询某次运行的所有角色执行记录"""
    runs = await service.list_role_runs(db, run_id)
    return ok(data=runs)
