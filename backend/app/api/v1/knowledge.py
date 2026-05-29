"""知识库 API"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination

router = APIRouter()


@router.get("/documents")
async def list_documents(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库文档列表"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": {"items": [], "total": 0}}


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上传知识库文档"""
    # TODO: 实现文件上传 + 向量化
    return {"code": 0, "message": "ok", "data": None}


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除知识库文档"""
    # TODO: 实现
    return {"code": 0, "message": "ok", "data": None}


@router.get("/search")
async def search(
    q: str = "",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """知识库语义搜索"""
    # TODO: 实现 Qdrant 向量搜索
    return {"code": 0, "message": "ok", "data": {"items": []}}
