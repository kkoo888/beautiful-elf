"""专家团工作流 Schema — 统一 camelCase"""
from typing import Optional, List
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


# ─── 专家成员 ─────────────────────────────────────────────

class ExpertMemberCreate(CamelModel):
    """创建专家成员"""
    member_name: str = Field(..., min_length=1, max_length=128, description="专家名称")
    member_role: str = Field(..., min_length=1, max_length=128, description="专家角色")
    avatar: str = Field(default="🤖", max_length=64, description="头像 emoji")
    system_prompt: str = Field(..., min_length=1, description="专家系统提示词")
    model_name: str = Field(default="", max_length=128, description="模型名称")
    temperature: int = Field(default=70, ge=0, le=200, description="温度 (x100)")
    max_tokens: int = Field(default=2048, ge=1, le=8192, description="最大 token 数")
    tools_json: Optional[List[dict]] = Field(default=None, description="可用工具列表")
    sort_order: int = Field(default=0, description="排序顺序")
    is_enabled: int = Field(default=1, ge=0, le=1, description="是否启用")


class ExpertMemberUpdate(CamelModel):
    """更新专家成员"""
    member_name: Optional[str] = Field(default=None, max_length=128)
    member_role: Optional[str] = Field(default=None, max_length=128)
    avatar: Optional[str] = Field(default=None, max_length=64)
    system_prompt: Optional[str] = Field(default=None)
    model_name: Optional[str] = Field(default=None, max_length=128)
    temperature: Optional[int] = Field(default=None, ge=0, le=200)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192)
    tools_json: Optional[List[dict]] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)
    is_enabled: Optional[int] = Field(default=None, ge=0, le=1)


class ExpertMemberOut(CamelModel):
    """专家成员输出"""
    id: int
    team_id: int
    member_name: str
    member_role: str
    avatar: str
    system_prompt: str
    model_name: str
    temperature: int
    max_tokens: int
    tools_json: Optional[List[dict]] = None
    sort_order: int
    is_enabled: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── 专家团 ───────────────────────────────────────────────

class ExpertTeamCreate(CamelModel):
    """创建专家团"""
    team_name: str = Field(..., min_length=1, max_length=256, description="专家团名称")
    description: str = Field(default="", max_length=1024, description="描述")
    icon: str = Field(default="👥", max_length=64, description="图标")
    category: str = Field(default="通用", max_length=64, description="分类")
    orchestrator_prompt: str = Field(default="", description="编排器系统提示词")
    synthesizer_prompt: str = Field(default="", description="汇总器系统提示词")
    max_rounds: int = Field(default=3, ge=1, le=10, description="最大讨论轮次")
    config_json: Optional[dict] = Field(default=None, description="扩展配置")
    members: List[ExpertMemberCreate] = Field(default=[], description="专家成员列表")


class ExpertTeamUpdate(CamelModel):
    """更新专家团"""
    team_name: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = Field(default=None, max_length=1024)
    icon: Optional[str] = Field(default=None, max_length=64)
    category: Optional[str] = Field(default=None, max_length=64)
    orchestrator_prompt: Optional[str] = Field(default=None)
    synthesizer_prompt: Optional[str] = Field(default=None)
    max_rounds: Optional[int] = Field(default=None, ge=1, le=10)
    is_enabled: Optional[int] = Field(default=None, ge=0, le=1)
    config_json: Optional[dict] = Field(default=None)
    members: Optional[List[ExpertMemberCreate]] = Field(default=None, description="专家成员列表（整体替换）")


class ExpertTeamOut(CamelModel):
    """专家团输出"""
    id: int
    team_name: str
    description: str
    icon: str
    category: str
    orchestrator_prompt: str
    synthesizer_prompt: str
    max_rounds: int
    is_enabled: int
    version: int
    config_json: Optional[dict] = None
    members: List[ExpertMemberOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── 运行记录 ─────────────────────────────────────────────

class ExpertTeamRunOut(CamelModel):
    """运行记录输出"""
    id: int
    team_id: int
    team_name: str = ""
    run_status: int
    trigger_type: int
    input_text: str
    output_text: str
    discussion_json: Optional[List[dict]] = None
    error_message: str = ""
    round_count: int
    token_usage: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: int
    created_at: Optional[datetime] = None


class ExpertTeamExecuteRequest(CamelModel):
    """执行专家团请求"""
    input_text: str = Field(..., min_length=1, description="用户输入")
    max_rounds: Optional[int] = Field(default=None, ge=1, le=10, description="覆盖最大轮次")


# ─── 讨论消息 ─────────────────────────────────────────────

class DiscussionMessage(CamelModel):
    """讨论过程中的单条消息"""
    round: int = Field(..., description="轮次")
    expert_name: str = Field(..., description="专家名称")
    expert_role: str = Field(..., description="专家角色")
    content: str = Field(..., description="发言内容")
    timestamp: str = Field(..., description="时间戳")


# ─── 角色技能绑定 ────────────────────────────────────────

class RoleSkillCreate(CamelModel):
    """绑定技能到角色"""
    skill_id: int = Field(..., description="技能 ID")
    priority: int = Field(default=0, ge=0, description="调用优先级")
    config_override: Optional[dict] = Field(default=None, description="配置覆盖")
    is_enabled: int = Field(default=1, ge=0, le=1, description="是否启用")


class RoleSkillUpdate(CamelModel):
    """更新角色技能绑定"""
    priority: Optional[int] = Field(default=None, ge=0)
    config_override: Optional[dict] = Field(default=None)
    is_enabled: Optional[int] = Field(default=None, ge=0, le=1)


class RoleSkillOut(CamelModel):
    """角色技能绑定输出"""
    id: int
    role_id: int
    skill_id: int
    skill_name: str = ""
    skill_display_name: str = ""
    skill_description: str = ""
    priority: int
    config_override: Optional[dict] = None
    is_enabled: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── 角色执行记录 ────────────────────────────────────────

class ExpertRoleRunOut(CamelModel):
    """角色执行记录输出"""
    id: int
    run_id: int
    role_id: int
    role_name: str
    run_status: int
    round_num: int
    input_json: Optional[dict] = None
    output_json: Optional[dict] = None
    skills_used: Optional[List[dict]] = None
    error_message: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: int
    token_usage: int
    created_at: Optional[datetime] = None
