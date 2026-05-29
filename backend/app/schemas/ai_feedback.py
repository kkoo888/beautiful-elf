"""AI 回答反馈 Schema"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class AIFeedbackCreate(BaseModel):
    conversation_id: Optional[int] = Field(default=None, description="会话 ID")
    question: str = Field(..., description="用户问题")
    answer: str = Field(..., description="AI 回答")
    feedback_type: int = Field(..., ge=0, le=1, description="反馈类型: 0=点赞, 1=踩")
    reason_tags: Optional[List[str]] = Field(default=None, description="原因标签")
    reason_text: str = Field(default="", max_length=2048, description="自由文本")
    trace_id: str = Field(default="", max_length=128, description="请求链路 ID")


class AIFeedbackOut(BaseModel):
    id: int
    conversation_id: Optional[int]
    question: str
    answer: str
    feedback_type: int
    reason_tags: Optional[List[str]]
    reason_text: str
    trace_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
