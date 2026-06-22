"""RAG 配置 API — 检索参数管理"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.rag_config_service import rag_config_service
from app.schemas.response import ApiResult

router = APIRouter()


class RagConfigUpdate(BaseModel):
    """RAG 配置更新请求"""
    chunkSize: Optional[int] = Field(default=None, ge=128, le=8192, description="分块大小（tokens）")
    chunkOverlap: Optional[int] = Field(default=None, ge=0, le=2048, description="分块重叠（tokens）")
    similarityTopK: Optional[int] = Field(default=None, ge=1, le=50, description="向量检索返回条数")
    bm25TopN: Optional[int] = Field(default=None, ge=1, le=100, description="BM25 检索返回条数")
    rrfK: Optional[int] = Field(default=None, ge=1, le=200, description="RRF 融合参数 k")
    rerankEnabled: Optional[bool] = Field(default=None, description="是否启用重排序")
    rerankTopN: Optional[int] = Field(default=None, ge=1, le=20, description="重排序后保留条数")
    embeddingModel: Optional[str] = Field(default=None, max_length=128, description="Embedding 模型名称")
    embeddingDimension: Optional[int] = Field(default=None, ge=64, le=4096, description="Embedding 向量维度")
    queryRewriteEnabled: Optional[bool] = Field(default=None, description="是否启用查询改写")


@router.get("/rag-config")
async def get_rag_config(db: AsyncSession = Depends(get_db)) -> ApiResult[dict]:
    """获取 RAG 配置（DB 无记录时返回默认值）"""
    config = await rag_config_service.get_config(db)
    return ApiResult(data=config)


@router.put("/rag-config")
async def update_rag_config(
    data: RagConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[dict]:
    """更新 RAG 配置"""
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        return ApiResult(code="VALIDATION", message="没有需要更新的字段")

    config = await rag_config_service.update_config(db, update_data)
    return ApiResult(data=config)
