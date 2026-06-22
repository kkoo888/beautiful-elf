"""大模型模型配置 — 从 llm_provider.models JSON 拆出独立表（方案 A）"""
from sqlalchemy import Column, String, Integer, Float, JSON, BigInteger, SmallInteger, Index, text
from app.models.base import BaseModel


class LLMModel(BaseModel):
    """大模型（隶属于某个供应商）"""
    __tablename__ = "llm_model"

    provider_id = Column(BigInteger().with_variant(Integer, 'sqlite'), nullable=False, comment="供应商 ID → llm_provider.id")
    model_name = Column(String(128), nullable=False, comment="实际调用名，如 gpt-4o、qwen3.5:7b")
    display_name = Column(String(128), nullable=False, default="", comment="前端显示名，如 GPT-4o")
    context_length = Column(Integer, nullable=False, default=1_000_000, comment="上下文窗口长度")
    max_tokens = Column(Integer, nullable=False, default=4096, comment="默认最大输出 token")
    temperature = Column(Float, nullable=False, default=0.7, comment="默认温度 0-2")
    capabilities = Column(JSON, nullable=False, default=dict, comment="能力标签: {vision, tools, streaming}")
    is_enabled = Column(SmallInteger, nullable=False, default=1, comment="是否启用: 1=启用 0=禁用")
    sort_order = Column(Integer, nullable=False, default=0, comment="排序权重，越小越靠前")
    remark = Column(String(256), nullable=False, server_default=text("''"), comment="备注")

    __table_args__ = (
        Index("idx_llm_model_provider_id", "provider_id"),
        Index("idx_llm_model_model_name", "model_name"),
        Index("idx_llm_model_is_enabled", "is_enabled"),
    )
