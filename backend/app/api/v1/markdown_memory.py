"""Markdown 记忆文件 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
业务逻辑全部在 markdown_memory_service 中
"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.markdown_memory_service import markdown_memory_service
from app.schemas.memory_v2 import (
    MarkdownMemoryCreate, MarkdownMemoryOut, MarkdownMemoryListOut,
)
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=ApiPageResult)
async def list_markdown_memories(
    pagination: PaginationParams = Depends(get_pagination),
    user_id: int = Query(default=0, alias="userId", description="用户 ID"),
    memory_type: str | None = Query(default=None, alias="memoryType", description="类型筛选"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取 Markdown 记忆列表"""
    items, total = await markdown_memory_service.list_memories(
        db, user_id=user_id, page=pagination.page,
        page_size=pagination.page_size, memory_type=memory_type,
    )
    return ApiPageResult(data=items, total=total)


@router.get("/today", response_model=ApiResult[MarkdownMemoryOut])
async def get_today_log(
    user_id: int = Query(default=0, alias="userId"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取今日 daily log"""
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    item = await markdown_memory_service.get_by_title(db, user_id, today)
    if not item:
        return ApiResult(data=None)
    return ApiResult(data=item)


@router.get("/{memory_id}", response_model=ApiResult[MarkdownMemoryOut])
async def get_markdown_memory(
    memory_id: int = Path(..., description="记忆 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取记忆详情"""
    try:
        item = await markdown_memory_service.get_memory(db, memory_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("MEMORY_NOT_FOUND", str(e), "请检查记忆 ID")


@router.post("", response_model=ApiResult[MarkdownMemoryOut])
async def create_or_update_memory(
    data: MarkdownMemoryCreate,
    user_id: int = Query(default=0, alias="userId"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """创建或更新 Markdown 记忆"""
    try:
        item = await markdown_memory_service.upsert_memory(db, user_id, data)
        return ApiResult(data=item, message="保存成功")
    except Exception as e:
        return api_error("MEMORY_CREATE_FAILED", str(e), "保存失败，请重试")


@router.post("/daily", response_model=ApiResult[MarkdownMemoryOut])
async def append_daily_log(
    content: str = Query(..., description="追加内容"),
    user_id: int = Query(default=0, alias="userId"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """追加到今日 daily log"""
    try:
        item = await markdown_memory_service.append_daily_log(db, user_id, content)
        return ApiResult(data=item, message="追加成功")
    except Exception as e:
        return api_error("MEMORY_APPEND_FAILED", str(e), "追加失败，请重试")


@router.delete("/{memory_id}")
async def delete_markdown_memory(
    memory_id: int = Path(..., description="记忆 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除记忆（软删除）"""
    try:
        await markdown_memory_service.delete_memory(db, memory_id)
        return ApiResult(message="删除成功")
    except Exception as e:
        return api_error("MEMORY_DELETE_FAILED", str(e), "删除失败")
