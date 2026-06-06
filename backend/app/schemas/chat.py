"""对话模块 Schema — 统一 CamelModel"""
from typing import List, Optional
from pydantic import Field
from app.schemas.base import CamelModel


class ChatMessage(CamelModel):
    """对话消息"""
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")


class ChatRequest(CamelModel):
    """对话请求"""
    provider_id: Optional[int] = Field(default=None, description="供应商 ID（必填）", alias="providerId")
    model_name: str = Field(default="", description="模型名称", alias="modelName")
    messages: List[ChatMessage] = Field(..., description="对话历史")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    max_tokens: int = Field(default=2048, ge=1, le=32768, description="最大 token", alias="maxTokens")
    stream: bool = Field(default=True, description="是否流式返回")


class ChatResponse(CamelModel):
    """对话响应"""
    content: str = Field(default="", description="回复内容")
    model: str = Field(default="", description="使用的模型")
    provider_type: str = Field(default="", description="供应商类型")
    token_count: int = Field(default=0, ge=0, description="Token 消耗量")
