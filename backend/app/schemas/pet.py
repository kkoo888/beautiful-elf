"""宠物属性 Schema"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class PetAttributeUpdate(BaseModel):
    """更新宠物属性"""
    hunger: Optional[int] = Field(None, ge=0, le=100, description="饥饿值")
    clean: Optional[int] = Field(None, ge=0, le=100, description="清洁值")
    mood: Optional[int] = Field(None, ge=0, le=100, description="心情值")
    health: Optional[int] = Field(None, ge=0, le=100, description="健康值")
    intimacy: Optional[int] = Field(None, ge=0, description="亲密度")
    level: Optional[int] = Field(None, ge=1, description="等级")
    exp: Optional[int] = Field(None, ge=0, description="经验值")


class PetAttributeOut(BaseModel):
    """宠物属性输出"""
    id: int
    hunger: int
    clean: int
    mood: int
    health: int
    intimacy: int
    level: int
    exp: int
    last_active_at: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PetInteractionCreate(BaseModel):
    """创建互动记录"""
    interaction_type: int = Field(..., ge=0, description="互动类型")
    effect_json: Optional[Any] = Field(None, description="属性变化效果")


class PetInteractionOut(BaseModel):
    """互动记录输出"""
    id: int
    pet_attribute_id: int
    interaction_type: int
    effect_json: Optional[Any] = None
    created_at: str

    class Config:
        from_attributes = True


class ModelScanRequest(BaseModel):
    """扫描模型目录请求"""
    dir_path: str = Field(..., description="模型目录路径")


class ModelInfo(BaseModel):
    """模型文件信息"""
    name: str = Field(..., description="模型文件名")
    path: str = Field(..., description="模型完整路径")
    size: int = Field(..., description="文件大小（字节）")


class ModelScanResponse(BaseModel):
    """扫描模型目录响应"""
    dir_path: str
    models: List[ModelInfo]
