"""大模型供应商配置模型"""
from sqlalchemy import Column, String, Text, Integer, JSON, Index
from app.models.base import BaseModel


class LLMProvider(BaseModel):
    """大模型供应商"""
    __tablename__ = "llm_provider"

    name = Column(String(128), nullable=False, comment="供应商显示名称")
    provider_type = Column(String(64), nullable=False, comment="供应商类型: openai/claude/deepseek/ollama/custom")
    base_url = Column(String(512), nullable=False, comment="API 基础地址")
    api_key = Column(Text, default="", comment="API Key (加密存储)")
    models = Column(JSON, nullable=False, default=list, comment="可用模型列表 JSON")
    is_enabled = Column(Integer, nullable=False, default=1, comment="是否启用: 1=启用 0=禁用")
    is_default = Column(Integer, nullable=False, default=0, comment="是否默认供应商: 1=是 0=否")
    description = Column(String(512), default="", comment="备注说明")

    __table_args__ = (
        Index("idx_llm_provider_is_enabled", "is_enabled"),
        Index("idx_llm_provider_type", "provider_type"),
    )
