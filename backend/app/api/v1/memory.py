"""长期记忆 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()


@router.get("", response_model=ApiPageResult)
async def list_memories(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取记忆列表"""
    # TODO: 实现
    return ApiPageResult(data=[], total=0)


@router.post("", response_model=ApiResult)
async def create_memory(
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """创建记忆"""
    # TODO: 实现
    return ApiResult(message="创建成功")


@router.delete("/{memory_id}", response_model=ApiResult)
async def delete_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除记忆"""
    # TODO: 实现
    return ApiResult(message="删除成功")


@router.get("/search", response_model=ApiResult)
async def search_memories(
    q: str = "",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """记忆语义搜索"""
    # TODO: 实现 Qdrant 向量搜索
    return ApiResult(data={"items": []})
