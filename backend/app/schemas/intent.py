"""意图 Schema — 统一 CamelModel"""
from typing import List, Optional
from pydantic import Field
from app.schemas.base import CamelModel


class IntentCreate(CamelModel):
    """创建意图请求"""
    name: str = Field(..., min_length=1, max_length=128, description="意图名称")
    description: str = Field(default="", max_length=512, description="意图描述")
    trigger_texts: List[str] = Field(..., alias="triggerTexts", min_length=1, description="触发词列表")
    target_module: str = Field(..., alias="targetModule", min_length=1, max_length=128, description="目标模块")
    metadata: Optional[dict] = Field(default=None, description="扩展元数据")


class IntentUpdate(CamelModel):
    """更新意图请求"""
    name: Optional[str] = Field(default=None, max_length=128, description="意图名称")
    description: Optional[str] = Field(default=None, max_length=512, description="意图描述")
    trigger_texts: Optional[List[str]] = Field(default=None, alias="triggerTexts", description="触发词列表")
    target_module: Optional[str] = Field(default=None, alias="targetModule", max_length=128, description="目标模块")
    metadata: Optional[dict] = Field(default=None, description="扩展元数据")


class IntentOut(CamelModel):
    """意图响应"""
    id: int = Field(..., description="意图 ID")
    name: str = Field(default="", description="意图名称")
    description: str = Field(default="", description="意图描述")
    trigger_texts: List[str] = Field(default_factory=list, alias="triggerTexts", description="触发词列表")
    target_module: str = Field(default="", alias="targetModule", description="目标模块")
    metadata: Optional[dict] = Field(default=None, description="扩展元数据")
    is_enabled: int = Field(default=1, alias="isEnabled", description="是否启用")


class IntentMatchOut(CamelModel):
    """意图匹配结果"""
    intent_id: int = Field(default=0, alias="intentId", description="意图 ID")
    intent_name: str = Field(default="", alias="intentName", description="意图名称")
    score: float = Field(default=0.0, description="匹配置信度")
    target_module: str = Field(default="", alias="targetModule", description="目标模块")
    trigger_texts: List[str] = Field(default_factory=list, alias="triggerTexts", description="触发词")
