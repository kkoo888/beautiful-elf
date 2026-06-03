"""行为日志 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.base import CamelModel


class ActionLogCreate(BaseModel):
    module: str = Field(..., max_length=64, description="模块名")
    action: str = Field(..., max_length=128, description="行为动作")
    params_summary: str = Field(default="", max_length=512, description="参数摘要")
    session_id: str = Field(default="", max_length=128, description="会话 ID")


class ActionLogOut(CamelModel):
    id: int
    module: str
    action: str
    params_summary: str
    session_id: str
    created_at: datetime
    updated_at: datetime
