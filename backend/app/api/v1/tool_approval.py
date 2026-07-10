"""工具审批白名单 API — 管理自动放行规则"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.repository.tool_approval_repo import ToolApprovalWhitelistRepository
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
repo = ToolApprovalWhitelistRepository()


# ── Schemas ──────────────────────────────────────────────

# 风险等级常量
RISK_LOW = 0
RISK_MEDIUM = 1
RISK_HIGH = 2
RISK_LEVEL_MAP = {0: "low", 1: "medium", 2: "high"}


class WhitelistCreate(BaseModel):
    tool_name: str = Field(..., min_length=1, max_length=128)
    path_pattern: str = Field(default="", max_length=512)
    command_pattern: str = Field(default="", max_length=1024)
    risk_level: int = Field(default=0, ge=0, le=2, description="0=low 1=medium 2=high")
    note: str = Field(default="", max_length=500)


class WhitelistOut(BaseModel):
    id: int
    tool_name: str
    path_pattern: str
    command_pattern: str
    risk_level: int
    risk_level_label: str = ""
    note: str
    hit_count: int
    created_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, obj):
        d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        d["risk_level_label"] = RISK_LEVEL_MAP.get(d.get("risk_level", 0), "low")
        # datetime → str，避免 Pydantic 校验报错
        if d.get("created_at") is not None:
            d["created_at"] = str(d["created_at"])
        return cls(**d)


# ── CRUD ─────────────────────────────────────────────────

@router.get("", response_model=ApiPageResult[WhitelistOut])
async def list_whitelist(
    pagination: PaginationParams = Depends(get_pagination),
    user_id: int = Query(default=0),
    tool_name: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    """获取白名单列表"""
    offset = (pagination.page - 1) * pagination.page_size
    filters = {"user_id": user_id}
    if tool_name:
        filters["tool_name"] = tool_name
    items = await repo.find_all(db, offset=offset, limit=pagination.page_size, **filters)
    total = await repo.count(db, **filters)
    return ApiPageResult(data=[WhitelistOut.from_orm_model(i) for i in items], total=total)


@router.post("", response_model=ApiResult[WhitelistOut])
async def create_whitelist(
    data: WhitelistCreate,
    user_id: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    """新增白名单规则"""
    item = await repo.create(db, {
        "user_id": user_id,
        "tool_name": data.tool_name,
        "path_pattern": data.path_pattern,
        "command_pattern": data.command_pattern,
        "risk_level": data.risk_level,
        "note": data.note,
    })
    return ApiResult(data=WhitelistOut.from_orm_model(item))


@router.delete("/{item_id}", response_model=ApiResult)
async def delete_whitelist(
    item_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """删除白名单规则"""
    await repo.soft_delete(db, item_id)
    return ApiResult(message="已删除")


@router.post("/check", response_model=ApiResult)
async def check_whitelist(
    tool_name: str = Query(...),
    path: str = Query(default=""),
    command: str = Query(default=""),
    user_id: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    """检查是否在白名单中"""
    match = await repo.find_match(db, user_id, tool_name, path, command)
    if match:
        await repo.increment_hit(db, match.id)
        return ApiResult(data={
            "allowed": True,
            "rule_id": match.id,
            "risk_level": RISK_LEVEL_MAP.get(match.risk_level, "low"),
            "note": match.note,
        })
    return ApiResult(data={"allowed": False})
