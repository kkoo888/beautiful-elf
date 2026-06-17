"""视频画廊 API"""
import os
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.video_gallery_service import VideoGalleryService, VIDEO_DIR
from app.schemas.video_gallery import (
    VideoGalleryCreate, VideoGalleryUpdate, VideoGalleryOut,
    VideoGenerateRequest,
)
from app.schemas.expert_team import PolishPromptRequest
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
service = VideoGalleryService()


@router.get("", response_model=ApiPageResult[VideoGalleryOut])
async def list_videos(
    tag: Optional[str] = Query(default=None, description="标签筛选"),
    enabled: Optional[int] = Query(default=None, ge=0, le=1, description="启用状态"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[VideoGalleryOut]:
    """获取视频列表"""
    items, total = await service.list_videos(
        db, page=pagination.page, page_size=pagination.page_size,
        tag=tag, enabled=enabled,
    )
    return ApiPageResult(data=items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.get("/tags", response_model=ApiResult[list[str]])
async def list_tags(db: AsyncSession = Depends(get_db)) -> ApiResult[list[str]]:
    """获取所有标签"""
    tags = await service.list_tags(db)
    return ApiResult(data=tags)


@router.get("/{video_id}", response_model=ApiResult[VideoGalleryOut])
async def get_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[VideoGalleryOut]:
    """获取视频详情"""
    video = await service.get_video(db, video_id)
    return ApiResult(data=video)


@router.post("", response_model=ApiResult[VideoGalleryOut])
async def create_video(
    data: VideoGalleryCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[VideoGalleryOut]:
    """创建视频记录"""
    video = await service.create_video(db, data)
    return ApiResult(data=video)


@router.put("/{video_id}", response_model=ApiResult[VideoGalleryOut])
async def update_video(
    video_id: int,
    data: VideoGalleryUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[VideoGalleryOut]:
    """更新视频"""
    video = await service.update_video(db, video_id, data)
    return ApiResult(data=video)


@router.delete("/{video_id}", response_model=ApiResult)
async def delete_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除视频"""
    await service.delete_video(db, video_id)
    return ApiResult(message="删除成功")


@router.post("/generate", response_model=ApiResult[dict])
async def generate_video(
    data: VideoGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[dict]:
    """生成视频 — 调用大模型"""
    result = await service.generate_video(db, data)
    return ApiResult(data=result)


@router.post("/generate-prompt", response_model=ApiResult[str])
async def generate_prompt(
    data: PolishPromptRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[str]:
    """根据描述生成视频提示词（英文，符合 Agnes Video V2.0 最佳实践）"""
    result = await service.generate_video_prompt(db, data)
    return ApiResult(data=result)


@router.get("/files/{filename}")
async def serve_video(filename: str, request: Request):
    """通过 API 访问视频文件（支持 Range 请求，浏览器播放必需）"""
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="视频不存在")

    file_size = os.path.getsize(file_path)
    content_type = "video/mp4"
    if filename.endswith(".webm"):
        content_type = "video/webm"
    elif filename.endswith(".mov"):
        content_type = "video/quicktime"

    range_header = request.headers.get("range")
    if range_header:
        # 解析 Range: bytes=start-end
        range_start = 0
        range_end = file_size - 1
        range_match = range_header.replace("bytes=", "").split("-")
        if range_match[0]:
            range_start = int(range_match[0])
        if range_match[1]:
            range_end = int(range_match[1])
        range_end = min(range_end, file_size - 1)
        content_length = range_end - range_start + 1

        def iter_file():
            with open(file_path, "rb") as f:
                f.seek(range_start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(65536, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        resp = StreamingResponse(
            iter_file(),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {range_start}-{range_end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Access-Control-Allow-Origin": "*",
            },
        )
        return resp

    # 无 Range：返回完整文件
    resp = FileResponse(file_path, media_type=content_type)
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp
