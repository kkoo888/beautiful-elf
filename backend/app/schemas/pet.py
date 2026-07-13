"""宠物属性 Schema"""
from typing import Optional, List, Any
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class PetAttributeUpdate(CamelModel):
    """更新宠物属性"""
    hunger: Optional[int] = Field(None, ge=0, le=100, description="饥饿值")
    clean: Optional[int] = Field(None, ge=0, le=100, description="清洁值")
    mood: Optional[int] = Field(None, ge=0, le=100, description="心情值")
    health: Optional[int] = Field(None, ge=0, le=100, description="健康值")
    intimacy: Optional[int] = Field(None, ge=0, description="亲密度")
    level: Optional[int] = Field(None, ge=1, description="等级")
    exp: Optional[int] = Field(None, ge=0, description="经验值")


class PetAttributeOut(CamelModel):
    """宠物属性输出"""
    id: int
    hunger: int
    clean: int
    mood: int
    health: int
    intimacy: int
    level: int
    exp: int
    last_active_at: datetime
    created_at: datetime
    updated_at: datetime


class PetInteractionCreate(CamelModel):
    """创建互动记录"""
    interaction_type: int = Field(..., ge=0, description="互动类型")
    effect_json: Optional[Any] = Field(None, description="属性变化效果")


class PetInteractionOut(CamelModel):
    """互动记录输出"""
    id: int
    pet_attribute_id: int
    interaction_type: int
    effect_json: Optional[Any] = None
    created_at: datetime


class ModelScanRequest(CamelModel):
    """扫描模型目录请求"""
    dir_path: str = Field(..., description="模型目录路径")


class ModelInfo(CamelModel):
    """模型文件信息"""
    name: str = Field(..., description="模型文件名")
    path: str = Field(..., description="模型完整路径")
    size: int = Field(..., description="文件大小（字节）")
    loadable: bool = Field(True, description="当前加载器是否支持（false=预览，不可加载）")


class ModelScanResponse(CamelModel):
    """扫描模型目录响应"""
    dir_path: str
    models: List[ModelInfo]


class ModelSwitchRequest(CamelModel):
    """切换模型请求"""
    model_path: str = Field(..., description="模型文件完整路径")
