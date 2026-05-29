"""工具管理 Schema"""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ToolCreate(BaseModel):
    name: str = Field(..., max_length=128, description="工具名称")
    display_name: str = Field(default="", max_length=256, description="显示名称")
    description: str = Field(..., max_length=1024, description="工具描述")
    module: str = Field(..., max_length=128, description="所属模块")
    json_schema: Any = Field(..., description="参数 JSON Schema")


class ToolUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=256, description="显示名称")
    description: Optional[str] = Field(default=None, max_length=1024, description="工具描述")
    module: Optional[str] = Field(default=None, max_length=128, description="所属模块")
    json_schema: Optional[Any] = Field(default=None, description="参数 JSON Schema")


class ToolOut(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    module: str
    json_schema: Any
    enabled: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolStatsOut(BaseModel):
    id: int
    tool_id: int
    call_count: int
    success_count: int
    fail_count: int
    avg_duration_ms: int
    last_called_at: Optional[datetime]

    model_config = {"from_attributes": True}
