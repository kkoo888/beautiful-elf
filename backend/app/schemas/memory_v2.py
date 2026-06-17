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


class DistillRequest(CamelModel):
    """提炼记忆请求（Hindsight Mission + Directives 模型）"""
    days: int = Field(default=7, ge=1, le=30, description="提取天数")
    mission: str = Field(
        default="提取技术决策、架构选型、踩坑经验、主人偏好。忽略寒暄和临时调试信息。",
        description="提炼指令（Mission — 告诉 LLM 提取什么、忽略什么）",
    )
    directives: List[str] = Field(
        default_factory=list,
        description="硬规则（Directives — 提炼时必须遵守的约束）",
    )
    categories: List[str] = Field(
        default_factory=lambda: ["decisions", "pitfalls", "preferences", "status"],
        description="提炼分类: decisions/pitfalls/preferences/status",
    )


class ObservationSourceOut(CamelModel):
    """提炼记忆关联源输出"""
    source_id: int = Field(default=0, alias="sourceId", description="关联记录 ID")
    log_id: int = Field(default=0, alias="logId", description="源日志 ID")
    log_title: str = Field(default="", alias="logTitle", description="源日志标题（日期）")
    evidence_quote: str = Field(default="", alias="evidenceQuote", description="关键引用")


class ObservationOut(CamelModel):
    """提炼记忆输出"""
    id: int = Field(default=0, description="ID")
    content: str = Field(default="", description="提炼内容（Markdown）")
    category: str = Field(default="decisions", description="分类")
    freshness: str = Field(default="new", description="新鲜度")
    source_days: int = Field(default=0, alias="sourceDays", description="来源日志天数")
    proof_count: int = Field(default=0, alias="proofCount", description="证据条数")
    sources: List[ObservationSourceOut] = Field(default_factory=list, description="关联源列表")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


class DistillResult(CamelModel):
    """提炼结果"""
    observations: List[ObservationOut] = Field(default_factory=list, description="提炼出的记忆列表")
    source_days: int = Field(default=0, alias="sourceDays", description="实际读取的日志天数")
    source_logs: List[str] = Field(default_factory=list, alias="sourceLogs", description="读取的日志标题列表")
    total_count: int = Field(default=0, alias="totalCount", description="提炼出的记忆条数")


class ObservationUpdate(CamelModel):
    """更新提炼记忆"""
    content: Optional[str] = Field(default=None, description="内容")
    category: Optional[str] = Field(default=None, description="分类")
    freshness: Optional[str] = Field(default=None, description="新鲜度")


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
