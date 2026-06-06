"""Markdown 记忆文件 Schema"""
from typing import List, Optional
from pydantic import Field
from app.schemas.base import CamelModel


class MarkdownMemoryCreate(CamelModel):
    """创建/更新 Markdown 记忆"""
    title: str = Field(..., min_length=1, max_length=256, description="文件标题")
    content: str = Field(..., min_length=1, description="Markdown 内容")
    memory_type: str = Field(default="daily", alias="memoryType", description="类型: daily/longterm/curated")


class MarkdownMemoryOut(CamelModel):
    """Markdown 记忆响应"""
    id: int = Field(..., description="ID")
    user_id: int = Field(default=0, alias="userId", description="用户 ID")
    title: str = Field(default="", description="文件标题")
    content: str = Field(default="", description="Markdown 内容")
    memory_type: str = Field(default="daily", alias="memoryType", description="类型")
    word_count: int = Field(default=0, alias="wordCount", description="字数")
    qdrant_synced: int = Field(default=0, alias="qdrantSynced", description="是否已同步向量")


class MarkdownMemoryListOut(CamelModel):
    """Markdown 记忆列表项（不含 content）"""
    id: int = Field(..., description="ID")
    title: str = Field(default="", description="文件标题")
    memory_type: str = Field(default="daily", alias="memoryType", description="类型")
    word_count: int = Field(default=0, alias="wordCount", description="字数")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


class CostRecordOut(CamelModel):
    """成本记录响应"""
    id: int = Field(default=0)
    user_id: int = Field(default=0, alias="userId")
    conversation_id: int = Field(default=0, alias="conversationId")
    model_name: str = Field(default="", alias="modelName")
    prompt_tokens: int = Field(default=0, alias="promptTokens")
    completion_tokens: int = Field(default=0, alias="completionTokens")
    total_tokens: int = Field(default=0, alias="totalTokens")
    cost_usd: float = Field(default=0.0, alias="costUsd")
    cost_cny: float = Field(default=0.0, alias="costCny")
    call_type: str = Field(default="chat", alias="callType")
    duration_ms: int = Field(default=0, alias="durationMs")


class CostSummaryOut(CamelModel):
    """成本汇总"""
    total_cost_cny: float = Field(default=0.0, alias="totalCostCny")
    total_cost_usd: float = Field(default=0.0, alias="totalCostUsd")
    total_tokens: int = Field(default=0, alias="totalTokens")
    call_count: int = Field(default=0, alias="callCount")
    by_model: List[dict] = Field(default_factory=list, alias="byModel")
    by_type: List[dict] = Field(default_factory=list, alias="byType")


class ContextDebugOut(CamelModel):
    """Context 调试信息"""
    system_prompt_chars: int = Field(default=0, alias="systemPromptChars")
    sources_used: List[str] = Field(default_factory=list, alias="sourcesUsed")
    parts: dict = Field(default_factory=dict, description="各部分的字符数")
    message_count: int = Field(default=0, alias="messageCount")
    tool_count: int = Field(default=0, alias="toolCount")
    total_estimated_tokens: int = Field(default=0, alias="totalEstimatedTokens")
