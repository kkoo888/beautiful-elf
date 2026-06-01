"""Prompt 版本管理模型"""
from sqlalchemy import Column, Integer, String, Text, Index
from app.models.base import BaseModel


class Prompt(BaseModel):
    __tablename__ = "prompt"

    name = Column(String(128), nullable=False, comment="Prompt 名称")
    content = Column(Text, nullable=False, comment="Prompt 内容")
    version = Column(Integer, nullable=False, default=1, comment="版本号")
    is_active = Column(Integer, nullable=False, default=0, comment="是否激活")
    description = Column(String(512), default="", comment="版本说明")

    __table_args__ = (
        Index("idx_prompt_name_version", "name", "version"),
        Index("idx_prompt_is_active", "name", "is_active"),
    )
