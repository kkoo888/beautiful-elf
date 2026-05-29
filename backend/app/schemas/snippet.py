"""代码片段 Schema"""
from typing import Optional, List
from pydantic import BaseModel, Field


class SnippetCreate(BaseModel):
    """创建代码片段"""
    title: str = Field(..., min_length=1, max_length=256, description="片段标题")
    content: str = Field(..., min_length=1, description="代码内容")
    language: str = Field("", max_length=64, description="编程语言")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class SnippetUpdate(BaseModel):
    """更新代码片段"""
    title: Optional[str] = Field(None, min_length=1, max_length=256, description="片段标题")
    content: Optional[str] = Field(None, min_length=1, description="代码内容")
    language: Optional[str] = Field(None, max_length=64, description="编程语言")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class SnippetOut(BaseModel):
    """代码片段输出"""
    id: int
    title: str
    content: str
    language: str
    use_count: int
    tags: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SnippetQuery(BaseModel):
    """代码片段查询参数"""
    language: Optional[str] = Field(None, description="按语言筛选")
    tag: Optional[str] = Field(None, description="按标签筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
