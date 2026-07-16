"""人格配置 Schema"""
from typing import Optional, Any, List
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class SoulConfigCreate(CamelModel):
    name: str = Field(..., max_length=128, description="助手名称")
    avatar_url: str = Field(default="", max_length=512, description="头像地址")
    personality: List[str] = Field(..., description="性格标签")
    speaking_style: str = Field(default="", max_length=256, description="说话风格")
    background: Optional[str] = Field(default=None, description="背景故事")
    system_prompt: str = Field(..., description="系统提示词")
    is_active: int = Field(default=1, ge=0, le=1, description="是否激活")


class SoulConfigUpdate(CamelModel):
    name: Optional[str] = Field(default=None, max_length=128, description="助手名称")
    avatar_url: Optional[str] = Field(default=None, max_length=512, description="头像地址")
    personality: Optional[List[str]] = Field(default=None, description="性格标签")
    speaking_style: Optional[str] = Field(default=None, max_length=256, description="说话风格")
    background: Optional[str] = Field(default=None, description="背景故事")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")
    is_active: Optional[int] = Field(default=None, ge=0, le=1, description="是否激活")


class SoulConfigOut(CamelModel):
    id: int
    name: str
    avatar_url: str
    personality: Any
    speaking_style: str
    background: Optional[str]
    system_prompt: str
    is_active: int
    created_at: datetime
    updated_at: datetime


class UploadAvatarResult(CamelModel):
    """头像上传结果"""
    path: str = Field(..., description="头像文件相对路径")
