"""长期记忆 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
业务逻辑全部在 memory_service 中
"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.memory_service import memory_service
from app.schemas.memory import MemoryCreate, MemoryOut, MemorySearchResponse
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


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
