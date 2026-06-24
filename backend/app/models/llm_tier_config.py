"""模型路由 tier 配置 — 每个 tier 可映射到不同模型"""
from sqlalchemy import Column, String, Integer, Float, BigInteger, SmallInteger, Index, text
from app.models.base import BaseModel


class LLMTierConfig(BaseModel):
    """模型路由 tier 配置"""
    __tablename__ = "llm_tier_config"

    tier = Column(String(4), nullable=False, comment="路由档位: S=轻量 M=标准 L=强力 XL=最强")
    provider_id = Column(BigInteger, nullable=False, comment="供应商 ID → llm_provider.id")
    model_name = Column(String(128), nullable=False, comment="模型名 → llm_model.model_name")
    fallback_model_name = Column(String(128), nullable=False, server_default=text("''"), comment="降级模型名")
    max_tokens = Column(Integer, nullable=False, default=4096, comment="该 tier 最大输出 token")
    temperature = Column(Float, nullable=False, default=0.7, comment="该 tier 默认温度")
    reasoning_enabled = Column(SmallInteger, nullable=False, default=0, comment="是否启用 extended thinking: 1=启用 0=禁用")
    is_enabled = Column(SmallInteger, nullable=False, default=1, comment="是否启用: 1=启用 0=禁用")

    __table_args__ = (
        Index("idx_tier_config_tier", "tier"),
        Index("idx_tier_config_provider_id", "provider_id"),
    )
