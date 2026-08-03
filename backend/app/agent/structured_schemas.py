"""Structured Output Pydantic Schema 定义

所有 LLM 结构化输出的 Schema 集中管理，配合 with_structured_output() 使用。
替代手动 JSON 解析，100% 保证输出格式正确。

规范依据:
  - OpenAI Structured Outputs (response_format.json_schema)
  - LangChain with_structured_output()
  - MCP outputSchema + structuredContent
"""
from typing import List, Optional
from pydantic import BaseModel, Field


# ── 评估结果（engine.py evaluator + eval_pipeline.py）──

class EvalDimensions(BaseModel):
    """评估维度分数"""
    accuracy: int = Field(description="准确性 1-10", ge=1, le=10)
    completeness: int = Field(description="完整性 1-10", ge=1, le=10)
    hallucination: int = Field(description="幻觉检测 1-10（越高越无幻觉）", ge=1, le=10)
    tool_usage: int = Field(description="工具使用 1-10", ge=1, le=10)
    memory_usage: int = Field(description="记忆引用 1-10", ge=1, le=10)


class EvaluationResult(BaseModel):
    """LLM-as-Judge 评估结果"""
    score: int = Field(description="综合评分 1-10", ge=1, le=10)
    passed: bool = Field(description="是否通过（score >= 6）")
    reason: str = Field(description="简短评估说明")
    dimensions: EvalDimensions = Field(description="各维度评分")


# ── 记忆摘要（memory_manager.py）──

class MemorySummary(BaseModel):
    """对话结构化摘要"""
    summary: str = Field(description="200字内的对话摘要")
    topics: List[str] = Field(default_factory=list, description="话题标签列表")
    decisions: List[str] = Field(default_factory=list, description="用户做出的决定")
    todos: List[str] = Field(default_factory=list, description="待办事项")


# ── 评估分数（eval_pipeline.py _llm_judge）──

class JudgeScore(BaseModel):
    """LLM 评估分数"""
    score: float = Field(description="回答质量评分 0.0-1.0", ge=0.0, le=1.0)


# ── 压缩摘要（compaction.py）──

class CompactionSummary(BaseModel):
    """结构化对话压缩摘要（对标 Hermes Agent）

    4 个 section，模型知道去哪找什么信息：
    - task_snapshot: 之前在做什么
    - in_progress_state: 进行到哪了
    - pending_user_asks: 用户提了但还没解决的
    - remaining_work: 还剩什么没做
    """
    task_snapshot: str = Field(default="", description="任务概览：之前在做什么（1-3 句话）")
    in_progress_state: str = Field(default="", description="进行中的状态：做到哪了，中间结果是什么")
    pending_user_asks: List[str] = Field(default_factory=list, description="用户提了但还没解决的问题或请求")
    remaining_work: List[str] = Field(default_factory=list, description="还没完成的工作项")
    key_points: List[str] = Field(default_factory=list, description="关键要点（技术决定、发现、结论）")
    relevant_files: List[str] = Field(default_factory=list, description="涉及的文件路径（最多 10 个）")


# ── 查询改写（context_engine.py）──

class RewrittenQuery(BaseModel):
    """查询改写结果"""
    rewritten_query: str = Field(description="改写后的精确查询，如果无需改写则返回原文")
    reason: str = Field(default="", description="改写原因（调试用）")


# ── Goal 模式结构化输出 ──────────────────────────────────

class SubtaskItem(BaseModel):
    """计划中的单个子任务"""
    id: int = Field(description="子任务编号，从 1 开始")
    title: str = Field(description="子任务标题，简明扼要")
    description: str = Field(default="", description="子任务详细描述")
    dependencies: List[int] = Field(default_factory=list, description="依赖的子任务 ID 列表")


class SubtaskPlan(BaseModel):
    """结构化执行计划 — 替代正则解析 [目标拆解]"""
    reasoning: str = Field(default="", description="规划思路（简要说明为什么这样拆解）")
    subtasks: List[SubtaskItem] = Field(description="子任务列表，按执行顺序排列")


class SubtaskResultItem(BaseModel):
    """单个子任务的执行结果摘要"""
    id: int = Field(description="子任务编号")
    title: str = Field(description="子任务标题")
    result_summary: str = Field(description="执行结果摘要，100字以内")
    tools_used: List[str] = Field(default_factory=list, description="使用的工具列表")
    success: bool = Field(description="是否成功完成")


class GoalReplanResult(BaseModel):
    """动态重规划结果 — 失败时 LLM 重新生成计划"""
    analysis: str = Field(default="", description="失败原因分析")
    strategy_change: str = Field(default="", description="策略调整说明")
    subtasks: List[SubtaskItem] = Field(description="重新规划的子任务列表")


class SemanticSubtaskValidation(BaseModel):
    """子任务语义校验结果"""
    completed: bool = Field(description="子任务是否实质完成")
    relevance: int = Field(description="与子任务目标的相关性 1-10", ge=1, le=10)
    quality_score: int = Field(description="输出质量 1-10", ge=1, le=10)
    has_hallucination: bool = Field(default=False, description="是否包含幻觉/捏造")
    issues: List[str] = Field(default_factory=list, description="发现的问题")
    suggestion: str = Field(default="", description="改进建议")


# ── RAG 分类器（借鉴 Vane Classifier 设计）────────────────

class RAGClassifierResult(BaseModel):
    """RAG 检索分类结果 — LLM 判断是否需要检索、检索什么类型

    借鉴 Vane classifier.ts 的多维分类设计：
    - skipSearch: 是否跳过检索（常识/闲聊/Widget可回答）
    - searchType: 检索类型（knowledge/web/all）
    - standaloneQuery: 脱离上下文的独立查询词
    - reason: 分类理由（调试用）
    """
    skip_search: bool = Field(
        description=(
            "是否可以不检索就回答。true=常识/闲聊/简单问题，" +
            "false=需要外部信息。拿不准时设 false"
        )
    )
    search_type: str = Field(
        default="knowledge",
        description="检索类型：knowledge=知识库, web=网页, all=全部"
    )
    standalone_query: str = Field(
        description=(
            "脱离对话上下文的独立查询词。" +
            "例如上下文讨论汽车，用户说'它们怎么工作'，" +
            "则 standalone_query='汽车怎么工作'"
        )
    )
    reason: str = Field(default="", description="分类理由（调试用，简短）")
