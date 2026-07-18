"""虚拟世界模型"""
from sqlalchemy import BigInteger, Integer, String, JSON, Float, Index
from sqlalchemy.dialects.mysql import SMALLINT, INTEGER
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel


class VirtualWorldScene(BaseModel):
    """虚拟世界场景"""
    __tablename__ = "virtual_world_scene"

    name: Mapped[str] = mapped_column(String(128), nullable=False, default="", comment="场景名称")
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="场景描述")
    width: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=32, comment="场景宽度（网格单位）")
    depth: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=32, comment="场景深度（网格单位）")
    height: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=16, comment="场景高度（网格单位）")
    ambient_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#ffffff", comment="环境光颜色")
    sky_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#87ceeb", comment="天空颜色")
    time_of_day: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=12, comment="时间(0-24)")
    is_active: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False, default=0, comment="是否激活: 1=是 0=否")

    __table_args__ = (
        Index("idx_virtual_world_scene_is_active", "is_active"),
        Index("idx_virtual_world_scene_is_deleted", "is_deleted"),
    )


class VirtualWorldBlock(BaseModel):
    """虚拟世界方块类型注册表"""
    __tablename__ = "virtual_world_block"

    block_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", comment="方块ID")
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="", comment="方块名称")
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="structure", comment="分类")
    geometry_type: Mapped[str] = mapped_column(String(32), nullable=False, default="box", comment="几何体类型")
    geometry_args: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, comment="几何体参数")
    default_material: Mapped[str] = mapped_column(String(64), nullable=False, default="default", comment="默认材质")
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="描述")
    tags: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="标签(逗号分隔)")
    sort_order: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0, comment="排序")

    __table_args__ = (
        Index("idx_virtual_world_block_block_id", "block_id"),
        Index("idx_virtual_world_block_category", "category"),
        Index("idx_virtual_world_block_is_deleted", "is_deleted"),
    )


class VirtualWorldSceneBlock(BaseModel):
    """场景中的方块实例"""
    __tablename__ = "virtual_world_scene_block"

    scene_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="场景ID")
    block_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", comment="方块类型ID")
    pos_x: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="X坐标")
    pos_y: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="Y坐标")
    pos_z: Mapped[float] = mapped_column(Float, nullable=False, default=0, comment="Z坐标")
    rotation_y: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0, comment="Y轴旋转(0/90/180/270)")
    material: Mapped[str] = mapped_column(String(64), nullable=False, default="", comment="材质覆盖(空=默认)")

    __table_args__ = (
        Index("idx_virtual_world_scene_block_scene_id", "scene_id"),
        Index("idx_virtual_world_scene_block_block_id", "block_id"),
        Index("idx_virtual_world_scene_block_is_deleted", "is_deleted"),
    )
