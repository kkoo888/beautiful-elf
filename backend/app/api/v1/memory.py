"""长期记忆 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination

router = APIRouter()


@router.get("")
async def list_memories(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    """获取记忆列表"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": {"items": [], "total": 0}}


@router.post("")
async def create_memory(
    db: AsyncSession = Depends(get_db),
):
    """创建记忆"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": None}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除记忆"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": None}


@router.get("/search")
async def search_memories(
    q: str = "",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """记忆语义搜索"""
    # TODO: 实现 Qdrant 向量搜索
    return {"code": 0, "message": "ok", "data": {"items": []}}
