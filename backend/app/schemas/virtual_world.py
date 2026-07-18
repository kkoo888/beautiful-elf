"""虚拟世界 Schema"""
from typing import Optional, List, Any
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


# ── Scene ──────────────────────────────────────────────

class VirtualWorldSceneCreate(CamelModel):
    """创建场景"""
    name: str = Field(..., min_length=1, max_length=128, description="场景名称")
    description: str = Field("", max_length=500, description="场景描述")
    width: int = Field(32, ge=1, le=256, description="宽度")
    depth: int = Field(32, ge=1, le=256, description="深度")
    height: int = Field(16, ge=1, le=128, description="高度")
    ambient_color: str = Field("#ffffff", max_length=16, description="环境光颜色")
    sky_color: str = Field("#87ceeb", max_length=16, description="天空颜色")
    time_of_day: int = Field(12, ge=0, le=24, description="时间(0-24)")
    is_active: int = Field(0, ge=0, le=1, description="是否激活")


class VirtualWorldSceneUpdate(CamelModel):
    """更新场景"""
    name: Optional[str] = Field(None, min_length=1, max_length=128, description="场景名称")
    description: Optional[str] = Field(None, max_length=500, description="场景描述")
    width: Optional[int] = Field(None, ge=1, le=256, description="宽度")
    depth: Optional[int] = Field(None, ge=1, le=256, description="深度")
    height: Optional[int] = Field(None, ge=1, le=128, description="高度")
    ambient_color: Optional[str] = Field(None, max_length=16, description="环境光颜色")
    sky_color: Optional[str] = Field(None, max_length=16, description="天空颜色")
    time_of_day: Optional[int] = Field(None, ge=0, le=24, description="时间(0-24)")
    is_active: Optional[int] = Field(None, ge=0, le=1, description="是否激活")


class VirtualWorldSceneOut(CamelModel):
    """场景输出"""
    id: int
    name: str
    description: str
    width: int
    depth: int
    height: int
    ambient_color: str
    sky_color: str
    time_of_day: int
    is_active: int
    created_at: datetime
    updated_at: datetime


# ── Block ──────────────────────────────────────────────

class VirtualWorldBlockCreate(CamelModel):
    """注册方块类型"""
    block_id: str = Field(..., min_length=1, max_length=64, description="方块ID")
    name: str = Field(..., min_length=1, max_length=128, description="方块名称")
    category: str = Field("structure", max_length=32, description="分类")
    geometry_type: str = Field("box", max_length=32, description="几何体类型")
    geometry_args: Any = Field(default_factory=dict, description="几何体参数")
    default_material: str = Field("default", max_length=64, description="默认材质")
    description: str = Field("", max_length=500, description="描述")
    tags: str = Field("", max_length=500, description="标签(逗号分隔)")
    sort_order: int = Field(0, ge=0, description="排序")


class VirtualWorldBlockOut(CamelModel):
    """方块类型输出"""
    id: int
    block_id: str
    name: str
    category: str
    geometry_type: str
    geometry_args: Any = {}
    default_material: str
    description: str
    tags: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


# ── SceneBlock ─────────────────────────────────────────

class VirtualWorldSceneBlockCreate(CamelModel):
    """放置方块"""
    block_id: str = Field(..., min_length=1, max_length=64, description="方块类型ID")
    pos_x: float = Field(0, description="X坐标")
    pos_y: float = Field(0, description="Y坐标")
    pos_z: float = Field(0, description="Z坐标")
    rotation_y: int = Field(0, ge=0, le=270, description="Y轴旋转(0/90/180/270)")
    material: str = Field("", max_length=64, description="材质覆盖")


class VirtualWorldSceneBlockOut(CamelModel):
    """场景方块实例输出"""
    id: int
    scene_id: int
    block_id: str
    pos_x: float
    pos_y: float
    pos_z: float
    rotation_y: int
    material: str
    created_at: datetime
    updated_at: datetime
