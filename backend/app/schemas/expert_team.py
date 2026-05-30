"""专家团工作流 Schema"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ─── 专家成员 ─────────────────────────────────────────────

class ExpertMemberCreate(BaseModel):
    """创建专家成员"""
    name: str = Field(..., min_length=1, max_length=128, description="专家名称")
    role: str = Field(..., min_length=1, max_length=128, description="专家角色")
    avatar: str = Field(default="🤖", max_length=64, description="头像 emoji")
    system_prompt: str = Field(..., min_length=1, description="专家系统提示词")
    model_name: str = Field(default="", max_length=128, description="模型名称")
    temperature: int = Field(default=70, ge=0, le=200, description="温度 (x100)")
    max_tokens: int = Field(default=2048, ge=1, le=8192, description="最大 token 数")
    tools_json: Optional[List[dict]] = Field(default=None, description="可用工具列表")
    sort_order: int = Field(default=0, description="排序顺序")
    enabled: int = Field(default=1, ge=0, le=1, description="是否启用")


class ExpertMemberUpdate(BaseModel):
    """更新专家成员"""
    name: Optional[str] = Field(default=None, max_length=128)
    role: Optional[str] = Field(default=None, max_length=128)
    avatar: Optional[str] = Field(default=None, max_length=64)
    system_prompt: Optional[str] = None
    model_name: Optional[str] = Field(default=None, max_length=128)
    temperature: Optional[int] = Field(default=None, ge=0, le=200)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192)
    tools_json: Optional[List[dict]] = None
    sort_order: Optional[int] = None
    enabled: Optional[int] = Field(default=None, ge=0, le=1)


class ExpertMemberOut(BaseModel):
    """专家成员输出"""
    id: int
    team_id: int
    name: str
    role: str
    avatar: str
    system_prompt: str
    model_name: str
    temperature: int
    max_tokens: int
    tools_json: Optional[List[dict]] = None
    sort_order: int
    enabled: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── 专家团 ───────────────────────────────────────────────

class ExpertTeamCreate(BaseModel):
    """创建专家团"""
    name: str = Field(..., min_length=1, max_length=256, description="专家团名称")
    description: str = Field(default="", max_length=1024, description="描述")
    icon: str = Field(default="👥", max_length=64, description="图标")
    category: str = Field(default="通用", max_length=64, description="分类")
    orchestrator_prompt: str = Field(default="", description="编排器系统提示词")
    synthesizer_prompt: str = Field(default="", description="汇总器系统提示词")
    max_rounds: int = Field(default=3, ge=1, le=10, description="最大讨论轮次")
    config_json: Optional[dict] = Field(default=None, description="扩展配置")
    members: List[ExpertMemberCreate] = Field(default=[], description="专家成员列表")


class ExpertTeamUpdate(BaseModel):
    """更新专家团"""
    name: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = Field(default=None, max_length=1024)
    icon: Optional[str] = Field(default=None, max_length=64)
    category: Optional[str] = Field(default=None, max_length=64)
    orchestrator_prompt: Optional[str] = None
    synthesizer_prompt: Optional[str] = None
    max_rounds: Optional[int] = Field(default=None, ge=1, le=10)
    enabled: Optional[int] = Field(default=None, ge=0, le=1)
    config_json: Optional[dict] = None


class ExpertTeamOut(BaseModel):
    """专家团输出"""
    id: int
    name: str
    description: str
    icon: str
    category: str
    orchestrator_prompt: str
    synthesizer_prompt: str
    max_rounds: int
    enabled: int
    version: int
    config_json: Optional[dict] = None
    members: List[ExpertMemberOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── 运行记录 ─────────────────────────────────────────────

class ExpertTeamRunOut(BaseModel):
    """运行记录输出"""
    id: int
    team_id: int
    team_name: str = ""
    status: int
    trigger_type: int
    input_text: str
    output_text: str
    discussion_json: Optional[List[dict]] = None
    error_message: str
    round_count: int
    token_usage: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpertTeamExecuteRequest(BaseModel):
    """执行专家团请求"""
    input_text: str = Field(..., min_length=1, description="用户输入")
    max_rounds: Optional[int] = Field(default=None, ge=1, le=10, description="覆盖最大轮次")


# ─── 讨论消息 ─────────────────────────────────────────────

class DiscussionMessage(BaseModel):
    """讨论过程中的单条消息"""
    round: int = Field(..., description="轮次")
    expert_name: str = Field(..., description="专家名称")
    expert_role: str = Field(..., description="专家角色")
    content: str = Field(..., description="发言内容")
    timestamp: str = Field(..., description="时间戳")
