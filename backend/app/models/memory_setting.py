"""记忆设置模型 — 记忆模块的开关/配置持久化"""
from sqlalchemy import Integer, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MemorySetting(BaseModel):
    __tablename__ = "memory_setting"

    setting_key: Mapped[str] = mapped_column(
        String(128), nullable=False, default="", unique=True, comment="设置键"
    )
    is_enabled: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="是否启用: 1=是 0=否"
    )
    interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="执行间隔(秒)"
    )
    provider_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="供应商 ID (关联 llm_provider)"
    )
    model_name: Mapped[str] = mapped_column(
        String(128), nullable=False, default="", comment="模型名称（如 qwen3.5:7b）"
    )
    description: Mapped[str] = mapped_column(
        String(512), nullable=False, default="", comment="设置说明"
    )
