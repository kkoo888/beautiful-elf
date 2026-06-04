"""知识库 API"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()


@router.get("/documents", response_model=ApiPageResult)
async def list_documents(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取知识库文档列表"""
    # TODO: 实现
    return ApiPageResult(data=[], total=0)


@router.post("/documents", response_model=ApiResult)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """上传知识库文档"""
    # TODO: 实现文件上传 + 向量化
    return ApiResult(message="上传成功")


@router.delete("/documents/{document_id}", response_model=ApiResult)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除知识库文档"""
    # TODO: 实现
    return ApiResult(message="删除成功")


@router.get("/search", response_model=ApiResult)
async def search(
    q: str = "",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """知识库语义搜索"""
    # TODO: 实现 Qdrant 向量搜索
    return ApiResult(data={"items": []})
