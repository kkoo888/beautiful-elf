"""长期记忆 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
业务逻辑全部在 memory_service 中
"""
from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.memory_service import memory_service
from app.schemas.memory import MemoryCreate, MemoryOut, MemorySearchResponse
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger
from app.repository.memory_setting_repo import MemorySettingRepository
from app.services.llm_provider_service import LLMProviderService

logger = get_logger(__name__)

router = APIRouter()


# ── 请求体 Schema ─────────────────────────────────────────

class OptimizeRequest(BaseModel):
    importance_boost: float = Field(default=1.0, ge=0.1, le=10.0, description="重要性加权系数")


class RescoreRequest(BaseModel):
    point_ids: list[str] = Field(default_factory=list, description="要重新评分的 Qdrant 点 ID（空=全部）")
    user_id: int = Field(default=0, description="用户 ID")


@router.get("", response_model=ApiPageResult)
async def list_memories(
    pagination: PaginationParams = Depends(get_pagination),
    conversation_id: int | None = Query(default=None, alias="conversationId", description="会话 ID 筛选"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取记忆列表"""
    items, total = await memory_service.list_memories(
        db, page=pagination.page, page_size=pagination.page_size,
        conversation_id=conversation_id,
    )
    return ApiPageResult(data=items, total=total)


@router.get("/search", response_model=ApiResult[MemorySearchResponse])
async def search_memories(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(default=10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[MemorySearchResponse]:
    """记忆语义搜索"""
    if not q.strip():
        return api_error("MEMORY_VALIDATION", "搜索关键词不能为空", "请输入搜索内容")

    result = await memory_service.search(db, query=q, limit=limit)
    return ApiResult(data=result)


@router.get("/optimize", response_model=ApiResult)
async def get_optimized_memories(
    rerank: bool = Query(default=True, description="启用 Rerank 精排"),
    decay: bool = Query(default=True, description="启用时间衰减"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
    q: str = Query(default="", description="搜索关键词（空=全量展示）"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取优化后的记忆列表（Rerank + Decay 效果展示）"""
    if not memory_service.memory_manager:
        return api_error("MEMORY_NOT_READY", "记忆管理器未初始化")

    try:
        query = q.strip() or "记忆 活跃 重要"
        results = await memory_service.memory_manager.search_with_scores(
            query=query, user_id=0, limit=limit,
            rerank=rerank, decay=decay,
        )

        items = []
        for r in results:
            items.append({
                "id": r.get("id", ""),
                "summary": r.get("summary", ""),
                "score": round(r.get("score", 0), 4),
                "rerankScore": round(r.get("rerank_score", 0), 4) if r.get("rerank_score") else None,
                "decayFactor": round(r.get("decay_factor", 1.0), 4),
                "importance": r.get("importance", 5),
                "activation": r.get("activation", 1.0),
                "tags": r.get("tags", []),
                "savedAt": r.get("saved_at", ""),
            })

        return ApiResult(data=items)
    except Exception as e:
        logger.error(f"获取优化记忆失败: {e}", exc_info=True)
        return api_error("MEMORY_OPTIMIZE_FAILED", str(e))


@router.post("/optimize", response_model=ApiResult)
async def trigger_optimization(
    data: OptimizeRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """触发记忆优化（重新计算 activation 并写回 Qdrant）"""
    if not memory_service.memory_manager:
        return api_error("MEMORY_NOT_READY", "记忆管理器未初始化")

    try:
        result = await memory_service.optimize_memories(importance_boost=data.importance_boost)
        logger.info(f"[optimize] 完成: {result}")
        return ApiResult(data=result)
    except Exception as e:
        logger.error(f"触发优化失败: {e}", exc_info=True)
        return api_error("MEMORY_OPTIMIZE_FAILED", str(e))


# ── 记忆设置 ──────────────────────────────────────────────

class MemoryTaskModelUpdate(BaseModel):
    model_name: str = Field(..., description="模型名称，如 qwen3.5:7b")


@router.get("/settings", response_model=ApiResult)
async def get_memory_settings(db: AsyncSession = Depends(get_db)) -> ApiResult:
    """获取记忆任务模型设置"""
    repo = MemorySettingRepository()
    setting = await repo.find_by_key(db, "memory_task_model")
    model_name = setting.model_name if setting else ""
    return ApiResult(data={"modelName": model_name})


@router.put("/settings", response_model=ApiResult)
async def update_memory_settings(
    data: MemoryTaskModelUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """更新记忆任务模型设置"""
    repo = MemorySettingRepository()
    setting = await repo.find_by_key(db, "memory_task_model")
    if setting:
        await repo.mapper.update(db, setting.id, {"model_name": data.model_name})
    else:
        await repo.mapper.create(db, {
            "setting_key": "memory_task_model",
            "is_enabled": 1,
            "model_name": data.model_name,
        })
    return ApiResult(data={"modelName": data.model_name})


@router.get("/settings/available-models", response_model=ApiResult)
async def list_available_models(db: AsyncSession = Depends(get_db)) -> ApiResult:
    """获取可用模型列表（来自已启用供应商的已启用模型）"""
    svc = LLMProviderService()
    providers = await svc.list_enabled_providers(db)
    models = []
    for p in providers:
        provider_out = p if hasattr(p, "models") else p
        provider_models = getattr(provider_out, "models", []) or []
        for m in provider_models:
            if getattr(m, "is_enabled", 1) == 1:
                models.append({
                    "providerName": getattr(provider_out, "name", ""),
                    "modelName": getattr(m, "model_name", ""),
                    "displayName": getattr(m, "display_name", "") or getattr(m, "model_name", ""),
                })
    return ApiResult(data=models)


@router.get("/{memory_id}", response_model=ApiResult[MemoryOut])
async def get_memory(
    memory_id: int = Path(..., description="记忆 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[MemoryOut]:
    """获取记忆详情"""
    try:
        item = await memory_service.get_memory(db, memory_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("MEMORY_NOT_FOUND", str(e), "请检查记忆 ID")


@router.post("", response_model=ApiResult[MemoryOut])
async def create_memory(
    data: MemoryCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[MemoryOut]:
    """创建记忆"""
    try:
        item = await memory_service.create_memory(db, data)
        return ApiResult(data=item)
    except Exception as e:
        logger.error(f"创建记忆失败: {e}", exc_info=True)
        return api_error("MEMORY_INTERNAL_ERROR", str(e), "创建记忆失败，请稍后重试")


@router.delete("/{memory_id}", response_model=ApiResult)
async def delete_memory(
    memory_id: int = Path(..., description="记忆 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除记忆"""
    try:
        await memory_service.delete_memory(db, memory_id)
        return ApiResult(message="删除成功")
    except Exception as e:
        return api_error("MEMORY_NOT_FOUND", str(e), "请检查记忆 ID")


@router.post("/rescore", response_model=ApiResult)
async def rescore_memories(
    data: RescoreRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """重新评分记忆重要性（LLM 精确评分）"""
    if not memory_service.memory_manager:
        return api_error("MEMORY_NOT_READY", "记忆管理器未初始化")

    try:
        result = await memory_service.rescore_memories(
            point_ids=data.point_ids,
            user_id=data.user_id,
        )
        return ApiResult(data=result)
    except Exception as e:
        logger.error(f"rescore 失败: {e}", exc_info=True)
        return api_error("MEMORY_RESCORE_FAILED", str(e))
