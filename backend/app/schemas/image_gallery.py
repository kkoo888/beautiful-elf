"""图片画廊 Schema — 统一 camelCase"""
from typing import Optional, List
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class ImageGalleryCreate(CamelModel):
    """创建图片"""
    name: str = Field(default="", max_length=256, description="图片名称（空则自动生成古风名）")
    prompt: str = Field(..., min_length=1, description="生成提示词")
    negative_prompt: str = Field(default="", description="反向提示词")
    model_name: str = Field(default="", max_length=128, description="模型名称")
    provider_id: int = Field(default=0, description="供应商 ID")
    file_path: str = Field(..., description="图片文件路径")
    thumbnail_path: str = Field(default="", description="缩略图路径")
    tags: str = Field(default="", max_length=1024, description="标签（逗号分隔）")
    width: int = Field(default=0, ge=0, description="图片宽度")
    height: int = Field(default=0, ge=0, description="图片高度")


class ImageGalleryUpdate(CamelModel):
    """更新图片"""
    name: Optional[str] = Field(default=None, max_length=256)
    prompt: Optional[str] = Field(default=None)
    negative_prompt: Optional[str] = Field(default=None)
    tags: Optional[str] = Field(default=None, max_length=1024)
    is_enabled: Optional[int] = Field(default=None, ge=0, le=1)


class ImageGalleryOut(CamelModel):
    """图片输出"""
    id: int
    name: str
    prompt: str
    negative_prompt: str
    model_name: str
    provider_id: int
    file_path: str
    thumbnail_path: str
    tags: str
    width: int
    height: int
    is_enabled: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ImageGenerateRequest(CamelModel):
    """生成图片请求"""
    prompt: str = Field(..., min_length=1, description="生成提示词")
    negative_prompt: str = Field(default="", description="反向提示词")
    model_name: str = Field(default="", max_length=128, description="模型名称")
    provider_id: int = Field(default=0, description="供应商 ID（0=使用默认）")
    width: int = Field(default=1024, ge=256, le=4096, description="图片宽度")
    height: int = Field(default=1024, ge=256, le=4096, description="图片高度")
