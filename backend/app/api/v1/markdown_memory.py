"""Markdown 记忆文件 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
业务逻辑全部在 markdown_memory_service 中

新增提炼记忆接口（借鉴 Hindsight）:
  - POST /distill: 结构化提炼，写入 observation 表
  - GET /observations: 列出提炼记忆
  - GET /observations/{id}: 单条详情
  - PUT /observations/{id}: 编辑单条
  - DELETE /observations/{id}: 删除单条
  - GET /observations/stats: 分类统计
"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.markdown_memory_service import markdown_memory_service
from app.schemas.memory_v2 import (
    MarkdownMemoryCreate, MarkdownMemoryOut, MarkdownMemoryListOut,
    DistillRequest, DistillResult, ObservationOut, ObservationUpdate,
)
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ── Markdown 记忆 CRUD ──────────────────────────────────

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


@router.get("/longterm", response_model=ApiResult[MarkdownMemoryOut])
async def get_longterm_memory(
    user_id: int = Query(default=0, alias="userId"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取长期记忆"""
    try:
        item = await markdown_memory_service.get_or_create_longterm(db, user_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("MEMORY_NOT_FOUND", str(e), "获取长期记忆失败")


@router.put("/longterm", response_model=ApiResult[MarkdownMemoryOut])
async def update_longterm_memory(
    data: MarkdownMemoryCreate,
    user_id: int = Query(default=0, alias="userId"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """更新长期记忆"""
    try:
        item = await markdown_memory_service.update_longterm(db, user_id, data.content)
        return ApiResult(data=item, message="保存成功")
    except Exception as e:
        return api_error("MEMORY_UPDATE_FAILED", str(e), "保存失败，请重试")


@router.get("/daily/list", response_model=ApiPageResult)
async def list_daily_logs(
    user_id: int = Query(default=0, alias="userId"),
    limit: int = Query(default=7, ge=1, le=30, description="返回天数"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取最近 N 天的 daily log 列表"""
    items = await markdown_memory_service.list_daily_logs(db, user_id, limit)
    return ApiPageResult(data=items, total=len(items))


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


# ── 提炼记忆（Observations）────────────────────────────

@router.post("/distill", response_model=ApiResult)
async def distill_memories(
    data: DistillRequest,
    user_id: int = Query(default=0, alias="userId"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """提炼记忆 — 异步执行，完成后通过 WebSocket 通知"""
    import asyncio
    from app.core.websocket_manager import ws_manager
    from app.core.database import AsyncSessionLocal

    async def _run_distill():
        try:
            async with AsyncSessionLocal() as bg_db:
                result = await markdown_memory_service.distill(
                    bg_db, user_id=user_id,
                    days=data.days, mission=data.mission,
                    directives=data.directives, categories=data.categories,
                )
                await bg_db.commit()
            await ws_manager.broadcast("default", {
                "type": "distill_complete",
                "data": {
                    "totalCount": result.total_count,
                    "observations": [
                        {"content": o.content, "category": o.category}
                        for o in result.observations
                    ],
                },
            })
        except Exception as e:
            logger.error(f"异步提炼记忆失败: {e}", exc_info=True)
            await ws_manager.broadcast("default", {
                "type": "distill_error",
                "data": {"message": str(e)},
            })

    asyncio.create_task(_run_distill())
    return ApiResult(message="提炼中，完成后将通过实时通知告知结果")


@router.get("/observations", response_model=ApiPageResult)
async def list_observations(
    pagination: PaginationParams = Depends(get_pagination),
    user_id: int = Query(default=0, alias="userId"),
    category: Optional[str] = Query(default=None, description="分类筛选"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取提炼记忆列表"""
    items, total = await markdown_memory_service.list_observations(
        db, user_id=user_id, category=category,
        page=pagination.page, page_size=pagination.page_size,
    )
    return ApiPageResult(data=items, total=total)


@router.get("/observations/stats", response_model=ApiResult)
async def get_observation_stats(
    user_id: int = Query(default=0, alias="userId"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取提炼记忆分类统计"""
    stats = await markdown_memory_service.get_category_stats(db, user_id)
    return ApiResult(data=stats)


@router.get("/observations/{obs_id}", response_model=ApiResult[ObservationOut])
async def get_observation(
    obs_id: int = Path(..., description="提炼记忆 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取单条提炼记忆详情（含关联源）"""
    try:
        item = await markdown_memory_service.get_observation(db, obs_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("MEMORY_OBSERVATION_NOT_FOUND", str(e), "请检查 ID")


@router.put("/observations/{obs_id}", response_model=ApiResult[ObservationOut])
async def update_observation(
    obs_id: int = Path(..., description="提炼记忆 ID"),
    data: ObservationUpdate = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """编辑单条提炼记忆"""
    try:
        item = await markdown_memory_service.update_observation(
            db, obs_id,
            content=data.content, category=data.category, freshness=data.freshness,
        )
        return ApiResult(data=item, message="更新成功")
    except Exception as e:
        return api_error("MEMORY_OBSERVATION_UPDATE_FAILED", str(e), "更新失败")


@router.delete("/observations/{obs_id}", response_model=ApiResult)
async def delete_observation(
    obs_id: int = Path(..., description="提炼记忆 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除单条提炼记忆"""
    try:
        await markdown_memory_service.delete_observation(db, obs_id)
        return ApiResult(message="删除成功")
    except Exception as e:
        return api_error("MEMORY_OBSERVATION_DELETE_FAILED", str(e), "删除失败")


@router.post("/observations/{obs_id}/sources", response_model=ApiResult)
async def create_observation_source(
    obs_id: int = Path(..., description="提炼记忆 ID"),
    source_memory_id: int = Query(..., alias="sourceMemoryId", description="源日志 ID"),
    evidence_quote: str = Query(default="", alias="evidenceQuote", description="关键引用"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """创建 observation 与 daily log 的关联"""
    try:
        result = await markdown_memory_service.create_observation_source(
            db, obs_id, source_memory_id, evidence_quote,
        )
        return ApiResult(data=result, message="关联创建成功")
    except Exception as e:
        return api_error("MEMORY_SOURCE_CREATE_FAILED", str(e), "关联失败")


@router.delete("/sources/{source_id}", response_model=ApiResult)
async def delete_observation_source(
    source_id: int = Path(..., description="关联记录 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除关联记录"""
    try:
        await markdown_memory_service.delete_observation_source(db, source_id)
        return ApiResult(message="关联已删除")
    except Exception as e:
        return api_error("MEMORY_SOURCE_DELETE_FAILED", str(e), "删除失败")


# ── 通用路由（放在最后）────────────────────────────────

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
        return api_error("MEMORY_CREATE_FAILED", str(e), "保存失败，请稍后重试")


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
