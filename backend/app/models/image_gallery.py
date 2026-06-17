"""图片画廊模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Index
from app.models.base import BaseModel


class ImageGallery(BaseModel):
    """图片画廊"""
    __tablename__ = "image_gallery"

    name = Column(String(256), nullable=False, comment="图片名称（古风名）")
    prompt = Column(Text, nullable=False, comment="生成提示词")
    negative_prompt = Column(Text, nullable=False, default="", comment="反向提示词")
    model_name = Column(String(128), nullable=False, default="", comment="生成模型名称")
    provider_id = Column(BigInteger, nullable=False, default=0, comment="供应商 ID")
    file_path = Column(String(1024), nullable=False, comment="图片文件路径")
    thumbnail_path = Column(String(1024), nullable=False, default="", comment="缩略图路径")
    tags = Column(String(1024), nullable=False, default="", comment="标签（逗号分隔）")
    width = Column(Integer, nullable=False, default=0, comment="图片宽度")
    height = Column(Integer, nullable=False, default=0, comment="图片高度")
    is_enabled = Column(Integer, nullable=False, default=1, comment="是否启用: 1=是 0=否")

    __table_args__ = (
        Index("idx_image_gallery_is_deleted_enabled", "is_deleted", "is_enabled"),
    )
