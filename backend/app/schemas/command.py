"""命令面板 Schema"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


def to_camel(s: str) -> str:
    """snake_case → camelCase"""
    parts = s.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class CommandCreate(BaseModel):
    """创建命令"""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=128, description="命令名称")
    display_name: str = Field("", max_length=256, description="显示名称", alias="displayName")
    description: str = Field("", max_length=512, description="命令描述")
    shortcut_key: str = Field("", max_length=32, description="快捷键", alias="shortcutKey")
    module: str = Field(..., min_length=1, max_length=64, description="所属模块")
    command_type: int = Field(0, ge=0, description="类型", alias="commandType")
    is_enabled: int = Field(1, ge=0, le=1, description="是否启用", alias="isEnabled")


class CommandUpdate(BaseModel):
    """更新命令"""
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, min_length=1, max_length=128, description="命令名称")
    display_name: Optional[str] = Field(None, max_length=256, description="显示名称", alias="displayName")
    description: Optional[str] = Field(None, max_length=512, description="命令描述")
    shortcut_key: Optional[str] = Field(None, max_length=32, description="快捷键", alias="shortcutKey")
    module: Optional[str] = Field(None, min_length=1, max_length=64, description="所属模块")
    command_type: Optional[int] = Field(None, ge=0, description="类型", alias="commandType")
    is_enabled: Optional[int] = Field(None, ge=0, le=1, description="是否启用", alias="isEnabled")


class CommandOut(BaseModel):
    """命令输出"""
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: int
    name: str
    display_name: str
    description: str
    shortcut_key: str
    module: str
    command_type: int
    is_enabled: int
    use_count: int = 0
    created_at: str
    updated_at: str


class CommandQuery(BaseModel):
    """命令查询参数"""
    model_config = ConfigDict(populate_by_name=True)

    module: Optional[str] = Field(None, description="按模块筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    is_enabled: Optional[int] = Field(None, description="按启用状态筛选", alias="isEnabled")
    sort_by: str = Field("id", description="排序字段: id / use_count", alias="sortBy")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量", alias="pageSize")
