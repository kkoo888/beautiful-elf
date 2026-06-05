"""工具管理 Schema"""
from typing import Optional, Any
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class ToolCreate(CamelModel):
    name: str = Field(..., max_length=128, description="工具名称")
    display_name: str = Field(default="", max_length=256, description="显示名称")
    description: str = Field(..., max_length=1024, description="工具描述")
    module: str = Field(..., max_length=128, description="所属模块")
    json_schema: Any = Field(..., description="参数 JSON Schema")
    risk_level: str = Field(default="low", description="风险等级: low/medium/high")


class ToolUpdate(CamelModel):
    display_name: Optional[str] = Field(default=None, max_length=256, description="显示名称")
    description: Optional[str] = Field(default=None, max_length=1024, description="工具描述")
    module: Optional[str] = Field(default=None, max_length=128, description="所属模块")
    json_schema: Optional[Any] = Field(default=None, description="参数 JSON Schema")
    risk_level: Optional[str] = Field(default=None, description="风险等级: low/medium/high")


class ToolOut(CamelModel):
    id: int
    name: str
    display_name: str
    description: str
    module: str
    json_schema: Any
    risk_level: str
    is_enabled: int
    created_at: datetime
    updated_at: datetime


class ToolStatsOut(CamelModel):
    id: int
    tool_id: int
    call_count: int
    success_count: int
    fail_count: int
    avg_duration_ms: int
    last_called_at: Optional[datetime]
