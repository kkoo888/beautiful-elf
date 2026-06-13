"""知识库 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
业务逻辑全部在 knowledge_service 中
"""
from fastapi import APIRouter, Depends, Path, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.knowledge_service import knowledge_service
from app.schemas.knowledge import KnowledgeDocumentOut, KnowledgeChunkOut, KnowledgeSearchResponse
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# SimpleDirectoryReader 内置支持的文件格式
ALLOWED_TYPES = {
    ".pdf", ".docx", ".pptx",
    ".xlsx", ".xls",
    ".csv", ".json", ".html",
    ".md", ".txt",
    ".epub", ".ipynb",
}
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB


@router.get("/documents", response_model=ApiPageResult)
async def list_documents(
    pagination: PaginationParams = Depends(get_pagination),
    status: int | None = Query(default=None, description="状态筛选 (0=待处理, 1=处理中, 2=完成, 3=失败)"),
    deleted: bool = Query(default=False, description="是否查询已删除文档"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取知识库文档列表"""
    items, total = await knowledge_service.list_documents(
        db, page=pagination.page, page_size=pagination.page_size,
        status=status, deleted_only=deleted,
    )
    return ApiPageResult(data=items, total=total)


@router.get("/documents/{document_id}", response_model=ApiResult[KnowledgeDocumentOut])
async def get_document(
    document_id: int = Path(..., description="文档 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[KnowledgeDocumentOut]:
    """获取文档详情"""
    try:
        item = await knowledge_service.get_document(db, document_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("KNOWLEDGE_NOT_FOUND", str(e), "请检查文档 ID")


@router.post("/documents", response_model=ApiResult[KnowledgeDocumentOut])
async def upload_document(
    file: UploadFile = File(..., description="上传文件 (PDF/DOCX/PPTX/XLSX/CSV/JSON/HTML/MD/TXT/EPUB/IPYNB)"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[KnowledgeDocumentOut]:
    """上传知识库文档"""
    # 校验文件类型
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_TYPES:
        return api_error(
            "KNOWLEDGE_VALIDATION",
            f"不支持的文件类型: {ext}",
            f"仅支持 {', '.join(ALLOWED_TYPES)} 格式",
        )

    # 读取文件内容
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return api_error(
            "KNOWLEDGE_VALIDATION",
            f"文件过大: {len(content)} bytes",
            "文件大小不能超过 200MB",
        )

    try:
        item = await knowledge_service.upload_document(
            db, filename=filename, file_type=ext.lstrip("."),
            file_size=len(content), file_content=content,
        )
        return ApiResult(data=item)
    except Exception as e:
        logger.error(f"文档上传失败: {e}", exc_info=True)
        return api_error("KNOWLEDGE_INTERNAL_ERROR", str(e), "文档上传失败，请稍后重试")


@router.delete("/documents/{document_id}", response_model=ApiResult)
async def delete_document(
    document_id: int = Path(..., description="文档 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除知识库文档"""
    try:
        await knowledge_service.delete_document(db, document_id)
        await db.commit()
        return ApiResult(message="删除成功")
    except Exception as e:
        return api_error("KNOWLEDGE_NOT_FOUND", str(e), "请检查文档 ID")


@router.get("/documents/{document_id}/chunks", response_model=ApiResult[list[KnowledgeChunkOut]])
async def list_chunks(
    document_id: int = Path(..., description="文档 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[list[KnowledgeChunkOut]]:
    """获取文档的分块列表"""
    try:
        chunks = await knowledge_service.list_chunks(db, document_id)
        return ApiResult(data=chunks)
    except Exception as e:
        return api_error("KNOWLEDGE_NOT_FOUND", str(e), "获取分块失败")


@router.post("/documents/{document_id}/restore", response_model=ApiResult)
async def restore_document(
    document_id: int = Path(..., description="文档 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """恢复被软删除的文档"""
    try:
        await knowledge_service.restore_document(db, document_id)
        await db.commit()
        return ApiResult(message="恢复成功")
    except Exception as e:
        return api_error("KNOWLEDGE_NOT_FOUND", str(e), "文档不存在或已删除")


@router.get("/search", response_model=ApiResult[KnowledgeSearchResponse])
async def search(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(default=10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[KnowledgeSearchResponse]:
    """知识库语义搜索"""
    if not q.strip():
        return api_error("KNOWLEDGE_VALIDATION", "搜索关键词不能为空", "请输入搜索内容")

    result = await knowledge_service.search(db, query=q, limit=limit)
    return ApiResult(data=result)
