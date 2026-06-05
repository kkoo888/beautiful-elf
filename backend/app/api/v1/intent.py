"""意图 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.intent_service import intent_service
from app.schemas.intent import IntentCreate, IntentUpdate, IntentOut, IntentMatchOut
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=ApiPageResult)
async def list_intents(
    pagination: PaginationParams = Depends(get_pagination),
    enabled: int | None = Query(default=None, description="启用状态筛选 (1=启用, 0=禁用)"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取意图列表"""
    items, total = await intent_service.list_intents(
        db, page=pagination.page, page_size=pagination.page_size, enabled=enabled,
    )
    return ApiPageResult(data=items, total=total)


@router.get("/{intent_id}", response_model=ApiResult[IntentOut])
async def get_intent(
    intent_id: int = Path(..., description="意图 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[IntentOut]:
    """获取意图详情"""
    try:
        item = await intent_service.get_intent(db, intent_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("INTENT_NOT_FOUND", str(e), "请检查意图 ID")


@router.post("", response_model=ApiResult[IntentOut])
async def create_intent(
    data: IntentCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[IntentOut]:
    """创建意图"""
    try:
        item = await intent_service.create_intent(db, data)
        return ApiResult(data=item)
    except Exception as e:
        logger.error(f"创建意图失败: {e}", exc_info=True)
        return api_error("INTENT_INTERNAL_ERROR", str(e), "创建意图失败，请稍后重试")


@router.put("/{intent_id}", response_model=ApiResult[IntentOut])
async def update_intent(
    intent_id: int = Path(..., description="意图 ID"),
    data: IntentUpdate = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[IntentOut]:
    """更新意图"""
    try:
        item = await intent_service.update_intent(db, intent_id, data)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("INTENT_NOT_FOUND", str(e), "请检查意图 ID")


@router.delete("/{intent_id}", response_model=ApiResult)
async def delete_intent(
    intent_id: int = Path(..., description="意图 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除意图"""
    try:
        await intent_service.delete_intent(db, intent_id)
        return ApiResult(message="删除成功")
    except Exception as e:
        return api_error("INTENT_NOT_FOUND", str(e), "请检查意图 ID")


@router.patch("/{intent_id}/enable", response_model=ApiResult[IntentOut])
async def enable_intent(
    intent_id: int = Path(..., description="意图 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[IntentOut]:
    """启用意图"""
    try:
        item = await intent_service.enable_intent(db, intent_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("INTENT_NOT_FOUND", str(e), "请检查意图 ID")


@router.patch("/{intent_id}/disable", response_model=ApiResult[IntentOut])
async def disable_intent(
    intent_id: int = Path(..., description="意图 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[IntentOut]:
    """禁用意图"""
    try:
        item = await intent_service.disable_intent(db, intent_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("INTENT_NOT_FOUND", str(e), "请检查意图 ID")


@router.post("/sync", response_model=ApiResult)
async def sync_intents(
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """全量同步意图向量到 Qdrant"""
    try:
        count = await intent_service.sync_all(db)
        return ApiResult(message=f"同步完成: {count} 个意图", data={"count": count})
    except Exception as e:
        logger.error(f"意图同步失败: {e}", exc_info=True)
        return api_error("INTENT_INTERNAL_ERROR", str(e), "意图同步失败，请稍后重试")


@router.get("/match/test", response_model=ApiResult[IntentMatchOut])
async def test_match(
    q: str = Query(..., description="测试文本"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[IntentMatchOut]:
    """测试意图匹配（调试用）"""
    if not intent_service.intent_router:
        return api_error("INTENT_INTERNAL_ERROR", "意图路由未初始化", "请等待系统初始化完成")

    result = await intent_service.intent_router.route(q)
    if not result:
        return ApiResult(data=IntentMatchOut(), message="未匹配到意图")

    return ApiResult(data=IntentMatchOut(
        intent_id=result["intent_id"],
        intent_name=result["intent_name"],
        score=result["score"],
        target_module=result["target_module"],
        trigger_texts=result["trigger_texts"],
    ))
