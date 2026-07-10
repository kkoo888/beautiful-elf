"""品牌资源 API — 仅处理文件上传，路径存入 setting 表"""
import os
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from app.schemas.response import ApiResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 品牌图片存储目录（backend/uploads/branding/）
BRANDING_DIR = os.path.join(os.path.dirname(__file__), '../../../uploads/branding')
os.makedirs(BRANDING_DIR, exist_ok=True)


class UploadResult(BaseModel):
    path: str


@router.post("/upload", response_model=ApiResult[UploadResult])
async def upload_branding_image(file: UploadFile = File(...)):
    """上传品牌图片，返回相对路径（调用方需自行存入 setting 表）"""
    if not file.content_type or not file.content_type.startswith('image/'):
        return api_error("BRANDING_INVALID_TYPE", "文件类型错误", "请上传图片文件")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        return api_error("BRANDING_FILE_TOO_LARGE", "文件过大", "最大 5MB")

    ext = os.path.splitext(file.filename or 'image.png')[1] or '.png'
    filename = f"bg_{hash(content) & 0xFFFFFFFF:08x}{ext}"
    filepath = os.path.join(BRANDING_DIR, filename)

    with open(filepath, 'wb') as f:
        f.write(content)

    relative_path = f"uploads/branding/{filename}"
    logger.info(f"[branding] 图片已上传: {relative_path}")
    return ApiResult(data=UploadResult(path=relative_path))
