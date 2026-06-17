"""图片画廊 API"""
import os
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.image_gallery_service import ImageGalleryService, IMAGE_DIR
from app.schemas.image_gallery import (
    ImageGalleryCreate, ImageGalleryUpdate, ImageGalleryOut,
    ImageGenerateRequest,
)
from app.schemas.expert_team import PolishPromptRequest
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
service = ImageGalleryService()


@router.get("", response_model=ApiPageResult[ImageGalleryOut])
async def list_images(
    tag: Optional[str] = Query(default=None, description="标签筛选"),
    enabled: Optional[int] = Query(default=None, ge=0, le=1, description="启用状态"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[ImageGalleryOut]:
    """获取图片列表"""
    items, total = await service.list_images(
        db, page=pagination.page, page_size=pagination.page_size,
        tag=tag, enabled=enabled,
    )
    return ApiPageResult(data=items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.get("/tags", response_model=ApiResult[list[str]])
async def list_tags(db: AsyncSession = Depends(get_db)) -> ApiResult[list[str]]:
    """获取所有标签"""
    tags = await service.list_tags(db)
    return ApiResult(data=tags)


@router.get("/{image_id}", response_model=ApiResult[ImageGalleryOut])
async def get_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ImageGalleryOut]:
    """获取图片详情"""
    image = await service.get_image(db, image_id)
    return ApiResult(data=image)


@router.post("", response_model=ApiResult[ImageGalleryOut])
async def create_image(
    data: ImageGalleryCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ImageGalleryOut]:
    """创建图片记录"""
    image = await service.create_image(db, data)
    return ApiResult(data=image)


@router.put("/{image_id}", response_model=ApiResult[ImageGalleryOut])
async def update_image(
    image_id: int,
    data: ImageGalleryUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ImageGalleryOut]:
    """更新图片"""
    image = await service.update_image(db, image_id, data)
    return ApiResult(data=image)


@router.delete("/{image_id}", response_model=ApiResult)
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除图片"""
    await service.delete_image(db, image_id)
    return ApiResult(message="删除成功")


@router.post("/generate", response_model=ApiResult[dict])
async def generate_image(
    data: ImageGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[dict]:
    """生成图片 — 调用大模型"""
    result = await service.generate_image(db, data)
    return ApiResult(data=result)


@router.post("/generate-prompt", response_model=ApiResult[str])
async def generate_prompt(
    data: PolishPromptRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[str]:
    """根据描述生成图片提示词"""
    result = await service.generate_prompt(db, data)
    return ApiResult(data=result)


@router.get("/files/{filename}")
async def serve_image(filename: str):
    """通过 API 访问图片文件（Electron 安全策略限制 file://）"""
    file_path = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(file_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="图片不存在")
    from fastapi.responses import FileResponse
    resp = FileResponse(file_path)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp
