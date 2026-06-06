"""大模型供应商 Schema"""
from typing import Optional, List
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class LLMModelItem(CamelModel):
    """模型列表中的单个模型"""
    id: str
    name: str
    context_length: int = 4096
    supports_vision: bool = False
    supports_tools: bool = False


class ProviderCreate(CamelModel):
    """创建供应商"""
    name: str
    provider_type: str  # openai/claude/deepseek/ollama/custom
    base_url: str
    api_key: str = ""
    models: List[LLMModelItem] = []
    is_enabled: int = 1
    is_default: int = 0
    description: str = ""


class ProviderUpdate(CamelModel):
    """更新供应商"""
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[List[LLMModelItem]] = None
    is_enabled: Optional[int] = None
    is_default: Optional[int] = None
    description: Optional[str] = None


class ProviderOut(CamelModel):
    """供应商输出"""
    id: int
    name: str
    provider_type: str
    base_url: str
    api_key: str  # 返回时脱敏为 ****
    models: List[LLMModelItem]
    is_enabled: int
    is_default: int
    description: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
