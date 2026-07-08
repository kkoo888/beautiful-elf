"""意图学习 Schema — 统一 CamelModel

ProactiveAgent 借鉴：
  - SkillSuggestionOut: 新增 ignoreCount / lastFeedback
  - AnalyzeResult: 新增 purpose / thoughts 分析过程
"""
from typing import List, Optional
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


# ── 纠正历史 ──────────────────────────────────────────────

class IntentCorrectionOut(CamelModel):
    """纠正历史响应"""
    id: int
    original_intent: str = Field(default="", alias="originalIntent", description="原始意图文本")
    correct_module: str = Field(default="", alias="correctModule", description="纠正后的目标模块")
    created_at: datetime = Field(alias="createdAt")


class IntentCorrectionCreate(CamelModel):
    """创建纠正记录"""
    original_intent: str = Field(..., alias="originalIntent", min_length=1, max_length=512, description="原始意图文本")
    correct_module: str = Field(..., alias="correctModule", min_length=1, max_length=128, description="纠正后的目标模块")


# ── 行为模式 ──────────────────────────────────────────────

class BehaviorPatternOut(CamelModel):
    """行为模式响应"""
    id: int
    description: str = Field(default="", description="模式描述")
    frequency: int = Field(default=0, description="触发频率")
    actions: List[str] = Field(default_factory=list, description="动作序列")
    is_solved: int = Field(default=0, alias="isSolved", description="是否已被技能覆盖")
    created_at: datetime = Field(alias="createdAt")


# ── 技能建议 ──────────────────────────────────────────────

class SkillSuggestionOut(CamelModel):
    """技能建议响应"""
    id: int
    pattern_id: int = Field(default=0, alias="patternId", description="关联的行为模式 ID")
    name: str = Field(default="", description="建议技能名称")
    description: str = Field(default="", description="建议描述")
    status: int = Field(default=0, description="状态: 0=待处理 1=已接受 2=已忽略")
    ignore_count: int = Field(default=0, alias="ignoreCount", description="连续忽略次数")
    last_feedback: str = Field(default="", alias="lastFeedback", description="最近反馈")
    created_at: datetime = Field(alias="createdAt")



