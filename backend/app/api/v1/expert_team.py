"""专家团工作流 API"""
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
)

router = APIRouter()
service = ExpertTeamService()


# ─── 专家团 CRUD ─────────────────────────────────────────

@router.get("")
async def list_expert_teams(
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
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total}}


@router.post("")
async def create_expert_team(
    data: ExpertTeamCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建专家团（含成员）"""
    team = await service.create_team(db, data)
    return {"code": 0, "message": "ok", "data": team}


@router.get("/{team_id}")
async def get_expert_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取专家团详情"""
    team = await service.get_team_by_id(db, team_id)
    return {"code": 0, "message": "ok", "data": team}


@router.put("/{team_id}")
async def update_expert_team(
    team_id: int,
    data: ExpertTeamUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新专家团"""
    team = await service.update_team(db, team_id, data)
    return {"code": 0, "message": "ok", "data": team}


@router.delete("/{team_id}")
async def delete_expert_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除专家团"""
    await service.delete_team(db, team_id)
    return {"code": 0, "message": "ok", "data": None}


# ─── 专家成员 ───────────────────────────────────────────

@router.post("/{team_id}/members")
async def add_expert_member(
    team_id: int,
    data: ExpertMemberCreate,
    db: AsyncSession = Depends(get_db),
):
    """添加专家成员"""
    member = await service.add_member(db, team_id, data)
    return {"code": 0, "message": "ok", "data": member}


@router.put("/members/{member_id}")
async def update_expert_member(
    member_id: int,
    data: ExpertMemberUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新专家成员"""
    update_data = data.model_dump(exclude_unset=True)
    member = await service.update_member(db, member_id, update_data)
    return {"code": 0, "message": "ok", "data": member}


@router.delete("/members/{member_id}")
async def delete_expert_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除专家成员"""
    await service.delete_member(db, member_id)
    return {"code": 0, "message": "ok", "data": None}


# ─── 执行与运行记录 ─────────────────────────────────────

@router.post("/{team_id}/execute")
async def execute_expert_team(
    team_id: int,
    data: ExpertTeamExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """执行专家团工作流"""
    result = await service.execute_team(db, team_id, data)
    return {"code": 0, "message": "ok", "data": result}


@router.get("/{team_id}/runs")
async def list_expert_team_runs(
    team_id: int,
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    """获取专家团运行记录"""
    items, total = await service.list_runs_by_team(
        db, team_id, page=pagination.page, page_size=pagination.page_size,
    )
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total}}


@router.get("/runs/all")
async def list_all_expert_runs(
    status: Optional[int] = Query(default=None, description="状态筛选"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    """获取所有专家团运行记录"""
    items, total = await service.list_all_runs(
        db, page=pagination.page, page_size=pagination.page_size, status=status,
    )
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total}}


@router.get("/runs/{run_id}")
async def get_expert_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取运行记录详情"""
    run = await service.get_run_by_id(db, run_id)
    return {"code": 0, "message": "ok", "data": run}
