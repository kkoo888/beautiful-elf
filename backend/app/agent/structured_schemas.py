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
    """对话压缩摘要"""
    key_points: List[str] = Field(description="关键要点列表")
    user_decisions: List[str] = Field(default_factory=list, description="用户决定")
    pending_tasks: List[str] = Field(default_factory=list, description="待办事项")
