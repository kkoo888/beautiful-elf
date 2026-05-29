"""命令面板 Schema"""
from typing import Optional
from pydantic import BaseModel, Field


class CommandCreate(BaseModel):
    """创建命令"""
    name: str = Field(..., min_length=1, max_length=128, description="命令名称")
    display_name: str = Field("", max_length=256, description="显示名称")
    description: str = Field("", max_length=512, description="命令描述")
    shortcut_key: str = Field("", max_length=32, description="快捷键")
    module: str = Field(..., min_length=1, max_length=64, description="所属模块")
    command_type: int = Field(0, ge=0, description="类型")
    enabled: int = Field(1, ge=0, le=1, description="是否启用")


class CommandUpdate(BaseModel):
    """更新命令"""
    name: Optional[str] = Field(None, min_length=1, max_length=128, description="命令名称")
    display_name: Optional[str] = Field(None, max_length=256, description="显示名称")
    description: Optional[str] = Field(None, max_length=512, description="命令描述")
    shortcut_key: Optional[str] = Field(None, max_length=32, description="快捷键")
    module: Optional[str] = Field(None, min_length=1, max_length=64, description="所属模块")
    command_type: Optional[int] = Field(None, ge=0, description="类型")
    enabled: Optional[int] = Field(None, ge=0, le=1, description="是否启用")


class CommandOut(BaseModel):
    """命令输出"""
    id: int
    name: str
    display_name: str
    description: str
    shortcut_key: str
    module: str
    command_type: int
    enabled: int
    use_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CommandQuery(BaseModel):
    """命令查询参数"""
    module: Optional[str] = Field(None, description="按模块筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    enabled: Optional[int] = Field(None, description="按启用状态筛选")
    sort_by: str = Field("id", description="排序字段: id / use_count")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
