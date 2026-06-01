"""技能管理 Schema"""
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class SkillCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., max_length=128, description="技能名称")
    display_name: str = Field(default="", max_length=256, description="显示名称", alias="displayName")
    description: str = Field(default="", max_length=1024, description="技能描述")
    version: str = Field(default="1.0.0", max_length=32, description="版本号")
    source: str = Field(default="", max_length=256, description="来源")
    trigger_words: Optional[List[str]] = Field(default=None, description="触发词列表", alias="triggerWords")
    dependencies: Optional[List[str]] = Field(default=None, description="依赖技能列表")
    config: Optional[Any] = Field(default=None, description="技能配置")


class SkillUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    display_name: Optional[str] = Field(default=None, max_length=256, description="显示名称", alias="displayName")
    description: Optional[str] = Field(default=None, max_length=1024, description="技能描述")
    version: Optional[str] = Field(default=None, max_length=32, description="版本号")
    source: Optional[str] = Field(default=None, max_length=256, description="来源")
    trigger_words: Optional[List[str]] = Field(default=None, description="触发词列表", alias="triggerWords")
    dependencies: Optional[List[str]] = Field(default=None, description="依赖技能列表")
    config: Optional[Any] = Field(default=None, description="技能配置")


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: int
    name: str
    display_name: str
    description: str
    version: str
    source: str
    trigger_words: Optional[List[str]]
    dependencies: Optional[List[str]]
    is_enabled: int
    config: Optional[Any]
    created_at: datetime
    updated_at: datetime


class SkillStatsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: int
    skill_id: int
    call_count: int
    success_count: int
    fail_count: int
    avg_duration_ms: int
    last_called_at: Optional[datetime]
