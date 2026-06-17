"""视频画廊模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, SmallInteger, Numeric, Index
from app.models.base import BaseModel


class VideoGallery(BaseModel):
    """视频画廊"""
    __tablename__ = "video_gallery"

    name = Column(String(256), nullable=False, default="", comment="视频名称")
    prompt = Column(Text, nullable=False, comment="生成提示词")
    negative_prompt = Column(Text, nullable=False, default="", comment="反向提示词")
    model_name = Column(String(128), nullable=False, default="", comment="生成模型名称")
    provider_id = Column(BigInteger().with_variant(BigInteger, 'mysql'), nullable=False, default=0, comment="供应商 ID")
    file_path = Column(String(1024), nullable=False, default="", comment="视频文件路径")
    thumbnail_path = Column(String(1024), nullable=False, default="", comment="缩略图路径")
    tags = Column(String(1024), nullable=False, default="", comment="标签（逗号分隔）")
    width = Column(Integer().with_variant(Integer, 'mysql'), nullable=False, default=0, comment="视频宽度")
    height = Column(Integer().with_variant(Integer, 'mysql'), nullable=False, default=0, comment="视频高度")
    num_frames = Column(Integer().with_variant(Integer, 'mysql'), nullable=False, default=0, comment="视频帧数")
    frame_rate = Column(Numeric(10, 2), nullable=False, default=0, comment="视频 FPS")
    duration = Column(Numeric(10, 2), nullable=False, default=0, comment="视频时长（秒）")
    is_enabled = Column(SmallInteger().with_variant(SmallInteger, 'mysql'), nullable=False, default=1, comment="是否启用: 1=是 0=否")

    __table_args__ = (
        Index("idx_video_gallery_is_deleted", "is_deleted"),
        Index("idx_video_gallery_is_enabled", "is_enabled"),
    )
