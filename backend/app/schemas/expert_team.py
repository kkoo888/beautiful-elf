"""专家团工作流 Schema — 符合 API 设计规范 (camelCase)"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ─── 专家成员 ─────────────────────────────────────────────

class ExpertMemberCreate(BaseModel):
    """创建专家成员"""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=128, description="专家名称")
    role: str = Field(..., min_length=1, max_length=128, description="专家角色")
    avatar: str = Field(default="🤖", max_length=64, description="头像 emoji", alias="avatar")
    system_prompt: str = Field(..., min_length=1, description="专家系统提示词", alias="systemPrompt")
    model_name: str = Field(default="", max_length=128, description="模型名称", alias="modelName")
    temperature: int = Field(default=70, ge=0, le=200, description="温度 (x100)", alias="temperature")
    max_tokens: int = Field(default=2048, ge=1, le=8192, description="最大 token 数", alias="maxTokens")
    tools_json: Optional[List[dict]] = Field(default=None, description="可用工具列表", alias="toolsJson")
    sort_order: int = Field(default=0, description="排序顺序", alias="sortOrder")
    enabled: int = Field(default=1, ge=0, le=1, description="是否启用")


class ExpertMemberUpdate(BaseModel):
    """更新专家成员"""
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=128)
    role: Optional[str] = Field(default=None, max_length=128)
    avatar: Optional[str] = Field(default=None, max_length=64)
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")
    model_name: Optional[str] = Field(default=None, max_length=128, alias="modelName")
    temperature: Optional[int] = Field(default=None, ge=0, le=200)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192, alias="maxTokens")
    tools_json: Optional[List[dict]] = Field(default=None, alias="toolsJson")
    sort_order: Optional[int] = Field(default=None, alias="sortOrder")
    enabled: Optional[int] = Field(default=None, ge=0, le=1)


class ExpertMemberOut(BaseModel):
    """专家成员输出"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    team_id: int = Field(alias="teamId")
    name: str
    role: str
    avatar: str
    system_prompt: str = Field(alias="systemPrompt")
    model_name: str = Field(alias="modelName")
    temperature: int
    max_tokens: int = Field(alias="maxTokens")
    tools_json: Optional[List[dict]] = Field(default=None, alias="toolsJson")
    sort_order: int = Field(alias="sortOrder")
    enabled: int
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


# ─── 专家团 ───────────────────────────────────────────────

class ExpertTeamCreate(BaseModel):
    """创建专家团"""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=256, description="专家团名称")
    description: str = Field(default="", max_length=1024, description="描述")
    icon: str = Field(default="👥", max_length=64, description="图标")
    category: str = Field(default="通用", max_length=64, description="分类")
    orchestrator_prompt: str = Field(default="", description="编排器系统提示词", alias="orchestratorPrompt")
    synthesizer_prompt: str = Field(default="", description="汇总器系统提示词", alias="synthesizerPrompt")
    max_rounds: int = Field(default=3, ge=1, le=10, description="最大讨论轮次", alias="maxRounds")
    config_json: Optional[dict] = Field(default=None, description="扩展配置", alias="configJson")
    members: List[ExpertMemberCreate] = Field(default=[], description="专家成员列表")


class ExpertTeamUpdate(BaseModel):
    """更新专家团"""
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = Field(default=None, max_length=1024)
    icon: Optional[str] = Field(default=None, max_length=64)
    category: Optional[str] = Field(default=None, max_length=64)
    orchestrator_prompt: Optional[str] = Field(default=None, alias="orchestratorPrompt")
    synthesizer_prompt: Optional[str] = Field(default=None, alias="synthesizerPrompt")
    max_rounds: Optional[int] = Field(default=None, ge=1, le=10, alias="maxRounds")
    enabled: Optional[int] = Field(default=None, ge=0, le=1)
    config_json: Optional[dict] = Field(default=None, alias="configJson")


class ExpertTeamOut(BaseModel):
    """专家团输出"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    name: str
    description: str
    icon: str
    category: str
    orchestrator_prompt: str = Field(alias="orchestratorPrompt")
    synthesizer_prompt: str = Field(alias="synthesizerPrompt")
    max_rounds: int = Field(alias="maxRounds")
    enabled: int
    version: int
    config_json: Optional[dict] = Field(default=None, alias="configJson")
    members: List[ExpertMemberOut] = []
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


# ─── 运行记录 ─────────────────────────────────────────────

class ExpertTeamRunOut(BaseModel):
    """运行记录输出"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    team_id: int = Field(alias="teamId")
    team_name: str = Field(default="", alias="teamName")
    status: int
    trigger_type: int = Field(alias="triggerType")
    input_text: str = Field(alias="inputText")
    output_text: str = Field(alias="outputText")
    discussion_json: Optional[List[dict]] = Field(default=None, alias="discussionJson")
    error_message: str = Field(default="", alias="errorMessage")
    round_count: int = Field(alias="roundCount")
    token_usage: int = Field(alias="tokenUsage")
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    finished_at: Optional[datetime] = Field(default=None, alias="finishedAt")
    duration_ms: int = Field(alias="durationMs")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")


class ExpertTeamExecuteRequest(BaseModel):
    """执行专家团请求"""
    model_config = ConfigDict(populate_by_name=True)

    input_text: str = Field(..., min_length=1, description="用户输入", alias="inputText")
    max_rounds: Optional[int] = Field(default=None, ge=1, le=10, description="覆盖最大轮次", alias="maxRounds")


# ─── 讨论消息 ─────────────────────────────────────────────

class DiscussionMessage(BaseModel):
    """讨论过程中的单条消息"""
    model_config = ConfigDict(populate_by_name=True)

    round: int = Field(..., description="轮次")
    expert_name: str = Field(..., description="专家名称", alias="expertName")
    expert_role: str = Field(..., description="专家角色", alias="expertRole")
    content: str = Field(..., description="发言内容")
    timestamp: str = Field(..., description="时间戳")


# ─── 角色技能绑定 ────────────────────────────────────────

class RoleSkillCreate(BaseModel):
    """绑定技能到角色"""
    model_config = ConfigDict(populate_by_name=True)

    skill_id: int = Field(..., description="技能 ID", alias="skillId")
    priority: int = Field(default=0, ge=0, description="调用优先级", alias="priority")
    config_override: Optional[dict] = Field(default=None, description="配置覆盖", alias="configOverride")
    enabled: int = Field(default=1, ge=0, le=1, description="是否启用")


class RoleSkillUpdate(BaseModel):
    """更新角色技能绑定"""
    model_config = ConfigDict(populate_by_name=True)

    priority: Optional[int] = Field(default=None, ge=0)
    config_override: Optional[dict] = Field(default=None, alias="configOverride")
    enabled: Optional[int] = Field(default=None, ge=0, le=1)


class RoleSkillOut(BaseModel):
    """角色技能绑定输出"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    role_id: int = Field(alias="roleId")
    skill_id: int = Field(alias="skillId")
    skill_name: str = Field(default="", alias="skillName")
    skill_display_name: str = Field(default="", alias="skillDisplayName")
    skill_description: str = Field(default="", alias="skillDescription")
    priority: int
    config_override: Optional[dict] = Field(default=None, alias="configOverride")
    enabled: int
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


# ─── 角色执行记录 ────────────────────────────────────────

class ExpertRoleRunOut(BaseModel):
    """角色执行记录输出"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    run_id: int = Field(alias="runId")
    role_id: int = Field(alias="roleId")
    role_name: str = Field(alias="roleName")
    status: int
    round_num: int = Field(alias="roundNum")
    input_json: Optional[dict] = Field(default=None, alias="inputJson")
    output_json: Optional[dict] = Field(default=None, alias="outputJson")
    skills_used: Optional[List[dict]] = Field(default=None, alias="skillsUsed")
    error_message: str = Field(default="", alias="errorMessage")
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    finished_at: Optional[datetime] = Field(default=None, alias="finishedAt")
    duration_ms: int = Field(alias="durationMs")
    token_usage: int = Field(alias="tokenUsage")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
