"""大模型供应商 + 模型 Schema — 方案 A: 两表分离"""
from typing import Optional, List
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


# ── 模型 Schema ─────────────────────────────────────────────

class LLMModelCreate(CamelModel):
    """创建模型"""
    model_name: str = Field(..., alias="modelName", description="实际调用名")
    display_name: str = Field(default="", alias="displayName", description="显示名")
    context_length: int = Field(default=1_000_000, alias="contextLength")
    max_tokens: int = Field(default=4096, alias="maxTokens")
    temperature: float = Field(default=0.7, description="温度 0-2")
    capabilities: dict = Field(default_factory=dict)
    is_enabled: int = Field(default=1, alias="isEnabled")
    sort_order: int = Field(default=0, alias="sortOrder")
    remark: str = ""


class LLMModelUpdate(CamelModel):
    """更新模型"""
    model_name: Optional[str] = Field(default=None, alias="modelName")
    display_name: Optional[str] = Field(default=None, alias="displayName")
    context_length: Optional[int] = Field(default=None, alias="contextLength")
    max_tokens: Optional[int] = Field(default=None, alias="maxTokens")
    temperature: Optional[float] = None
    capabilities: Optional[dict] = None
    is_enabled: Optional[int] = Field(default=None, alias="isEnabled")
    sort_order: Optional[int] = Field(default=None, alias="sortOrder")
    remark: Optional[str] = None


class LLMModelOut(CamelModel):
    """模型输出"""
    id: int
    provider_id: int = Field(alias="providerId")
    model_name: str = Field(alias="modelName")
    display_name: str = Field(default="", alias="displayName")
    context_length: int = Field(default=1_000_000, alias="contextLength")
    max_tokens: int = Field(default=4096, alias="maxTokens")
    temperature: float = Field(default=0.7)
    capabilities: dict = Field(default_factory=dict)
    is_enabled: int = Field(default=1, alias="isEnabled")
    sort_order: int = Field(default=0, alias="sortOrder")
    remark: str = Field(default="")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


# ── 供应商 Schema ────────────────────────────────────────────

class ProviderCreate(CamelModel):
    """创建供应商（可附带模型列表）"""
    name: str
    provider_type: str = Field(alias="providerType")
    base_url: str = Field(alias="baseUrl")
    api_key: str = Field(default="", alias="apiKey")
    is_enabled: int = Field(default=1, alias="isEnabled")
    is_default: int = Field(default=0, alias="isDefault")
    description: str = ""
    models: List[LLMModelCreate] = Field(default_factory=list, description="附带的模型列表")


class ProviderUpdate(CamelModel):
    """更新供应商"""
    name: Optional[str] = None
    provider_type: Optional[str] = Field(default=None, alias="providerType")
    base_url: Optional[str] = Field(default=None, alias="baseUrl")
    api_key: Optional[str] = Field(default=None, alias="apiKey")
    is_enabled: Optional[int] = Field(default=None, alias="isEnabled")
    is_default: Optional[int] = Field(default=None, alias="isDefault")
    description: Optional[str] = None
    models: Optional[List[LLMModelCreate]] = Field(default=None, description="模型列表（传入则全量同步）")


class ProviderOut(CamelModel):
    """供应商输出（含模型列表）"""
    id: int
    name: str
    provider_type: str = Field(alias="providerType")
    base_url: str = Field(alias="baseUrl")
    api_key: str = Field(default="", alias="apiKey")
    is_enabled: int = Field(default=1, alias="isEnabled")
    is_default: int = Field(default=0, alias="isDefault")
    description: str = Field(default="")
    models: List[LLMModelOut] = Field(default_factory=list, description="该供应商下的模型列表")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
