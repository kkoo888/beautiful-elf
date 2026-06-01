"""系统配置模型"""
from sqlalchemy import Column, Integer, String, Text, JSON, Index
from app.models.base import BaseModel


class Setting(BaseModel):
    __tablename__ = "setting"

    settings_key = Column(String(128), nullable=False, unique=True, comment="配置键")
    key_value = Column(Text, nullable=False, comment="配置值 (JSON)")
    description = Column(String(512), default="", comment="配置说明")
    restart_required = Column(Integer, nullable=False, default=0, comment="是否需要重启")

    __table_args__ = (
        Index("idx_setting_is_deleted", "is_deleted"),
    )


class SoulConfig(BaseModel):
    __tablename__ = "soul_config"

    name = Column(String(128), nullable=False, comment="助手名称")
    avatar_url = Column(String(512), default="", comment="头像地址")
    personality = Column(JSON, nullable=False, comment="性格标签")
    speaking_style = Column(String(256), default="", comment="说话风格")
    background = Column(Text, default=None, comment="背景故事")
    system_prompt = Column(Text, nullable=False, comment="系统提示词")
    is_active = Column(Integer, nullable=False, default=1, comment="是否激活")

    __table_args__ = (
        Index("idx_soul_config_is_active", "is_active"),
    )
