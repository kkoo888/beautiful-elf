"""Prompt 版本管理 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PromptCreate(BaseModel):
    name: str = Field(..., max_length=128, description="Prompt 名称")
    content: str = Field(..., description="Prompt 内容")
    description: str = Field(default="", max_length=512, description="版本说明")


class PromptUpdate(BaseModel):
    content: Optional[str] = Field(default=None, description="Prompt 内容")
    description: Optional[str] = Field(default=None, max_length=512, description="版本说明")


class PromptOut(BaseModel):
    id: int
    name: str
    content: str
    version: int
    is_active: int
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
