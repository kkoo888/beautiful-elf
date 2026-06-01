"""大模型供应商 Schema"""
from typing import Optional, List
from pydantic import BaseModel


class LLMModelItem(BaseModel):
    """模型列表中的单个模型"""
    id: str
    name: str
    context_length: int = 4096
    supports_vision: bool = False
    supports_tools: bool = False


class ProviderCreate(BaseModel):
    """创建供应商"""
    name: str
    provider_type: str  # openai/claude/deepseek/ollama/custom
    base_url: str
    api_key: str = ""
    models: List[LLMModelItem] = []
    enabled: int = 1
    is_default: int = 0
    description: str = ""


class ProviderUpdate(BaseModel):
    """更新供应商"""
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[List[LLMModelItem]] = None
    enabled: Optional[int] = None
    is_default: Optional[int] = None
    description: Optional[str] = None


class ProviderOut(BaseModel):
    """供应商输出"""
    id: int
    name: str
    provider_type: str
    base_url: str
    api_key: str  # 返回时脱敏为 ****
    models: List[LLMModelItem]
    enabled: int
    is_default: int
    description: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
