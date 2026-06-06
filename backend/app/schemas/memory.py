"""长期记忆 Schema — 统一 CamelModel"""
from typing import List, Optional
from pydantic import Field
from app.schemas.base import CamelModel


class MemoryCreate(CamelModel):
    """创建记忆请求"""
    conversation_id: Optional[int] = Field(default=None, alias="conversationId", description="来源会话 ID")
    summary: str = Field(..., min_length=1, max_length=2000, description="记忆摘要")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    importance: int = Field(default=5, ge=1, le=10, description="重要度 (1-10)")


class MemoryOut(CamelModel):
    """记忆响应"""
    id: int = Field(..., description="记忆 ID")
    conversation_id: Optional[int] = Field(default=None, alias="conversationId", description="来源会话 ID")
    summary: str = Field(default="", description="记忆摘要")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    importance: int = Field(default=5, description="重要度")


class MemorySearchResult(CamelModel):
    """记忆搜索结果"""
    id: int = Field(default=0, description="记忆 ID")
    summary: str = Field(default="", description="记忆摘要")
    score: float = Field(default=0.0, description="相关度分数")
    tags: List[str] = Field(default_factory=list, description="标签")


class MemorySearchResponse(CamelModel):
    """记忆搜索响应"""
    items: List[MemorySearchResult] = Field(default_factory=list, description="搜索结果")
    total: int = Field(default=0, description="结果总数")
