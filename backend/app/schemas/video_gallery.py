"""视频画廊 Schema — 统一 camelCase"""
from typing import Optional, List
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class VideoGalleryCreate(CamelModel):
    """创建视频"""
    name: str = Field(default="", max_length=256, description="视频名称")
    prompt: str = Field(..., min_length=1, description="生成提示词")
    negative_prompt: str = Field(default="", description="反向提示词")
    model_name: str = Field(default="", max_length=128, description="模型名称")
    provider_id: int = Field(default=0, description="供应商 ID")
    file_path: str = Field(..., description="视频文件路径")
    thumbnail_path: str = Field(default="", description="缩略图路径")
    tags: str = Field(default="", max_length=1024, description="标签（逗号分隔）")
    width: int = Field(default=0, ge=0, description="视频宽度")
    height: int = Field(default=0, ge=0, description="视频高度")
    num_frames: int = Field(default=0, ge=0, description="视频帧数")
    frame_rate: float = Field(default=0, ge=0, description="视频 FPS")
    duration: float = Field(default=0, ge=0, description="视频时长（秒）")


class VideoGalleryUpdate(CamelModel):
    """更新视频"""
    name: Optional[str] = Field(default=None, max_length=256)
    prompt: Optional[str] = Field(default=None)
    negative_prompt: Optional[str] = Field(default=None)
    tags: Optional[str] = Field(default=None, max_length=1024)
    is_enabled: Optional[int] = Field(default=None, ge=0, le=1)


class VideoGalleryOut(CamelModel):
    """视频输出"""
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
    num_frames: int
    frame_rate: float
    duration: float
    is_enabled: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VideoGenerateRequest(CamelModel):
    """生成视频请求"""
    prompt: str = Field(..., min_length=1, description="生成提示词")
    negative_prompt: str = Field(default="", description="反向提示词")
    model_name: str = Field(default="", max_length=128, description="模型名称")
    provider_id: int = Field(default=0, description="供应商 ID（0=使用默认）")
    image: Optional[str] = Field(default=None, description="参考图片 URL 或 Data URI（图生视频）")
    images: Optional[List[str]] = Field(default=None, description="多图 URL 列表（多图视频/关键帧）")
    mode: Optional[str] = Field(default=None, description="生成模式：ti2vid / keyframes")
    width: int = Field(default=1152, ge=256, le=1920, description="视频宽度")
    height: int = Field(default=768, ge=256, le=1920, description="视频高度")
    num_frames: int = Field(default=121, ge=9, le=441, description="视频帧数（≤441，8n+1）")
    frame_rate: float = Field(default=24, ge=1, le=60, description="视频 FPS")
    num_inference_steps: Optional[int] = Field(default=None, description="推理步数")
    seed: Optional[int] = Field(default=None, description="随机种子")
