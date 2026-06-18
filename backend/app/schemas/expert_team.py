"""专家团工作流 Schema — 统一 camelCase"""
from typing import Optional, List
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


# ─── 专家（独立实体）─────────────────────────────────────

class ExpertCreate(CamelModel):
    """创建专家"""
    member_name: str = Field(..., min_length=1, max_length=128, description="专家名称")
    member_role: str = Field(..., min_length=1, max_length=128, description="专家角色")
    avatar: str = Field(default="🤖", description="头像 emoji 或 base64 小图")
    goal: str = Field(default="", max_length=500, description="专家目标 — 驱动决策方向")
    backstory: str = Field(default="", max_length=1000, description="专家背景 — 丰富角色人格")
    system_prompt: str = Field(..., min_length=1, description="专家系统提示词")
    model_name: str = Field(default="", max_length=128, description="模型名称")
    provider_id: Optional[int] = Field(default=None, description="供应商 ID")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度 0-2")
    max_tokens: int = Field(default=2048, ge=1, le=8192, description="最大 token 数")
    tools_json: Optional[List[dict]] = Field(default=None, description="可用工具列表")
    allow_delegation: bool = Field(default=False, description="是否允许委派子任务给队友")
    max_execution_time: int = Field(default=120, ge=10, le=600, description="最大执行时间（秒）")
    is_enabled: int = Field(default=1, ge=0, le=1, description="是否启用")


class ExpertUpdate(CamelModel):
    """更新专家"""
    member_name: Optional[str] = Field(default=None, max_length=128)
    member_role: Optional[str] = Field(default=None, max_length=128)
    avatar: Optional[str] = Field(default=None)
    goal: Optional[str] = Field(default=None, max_length=500)
    backstory: Optional[str] = Field(default=None, max_length=1000)
    system_prompt: Optional[str] = Field(default=None)
    model_name: Optional[str] = Field(default=None, max_length=128)
    provider_id: Optional[int] = Field(default=None)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192)
    tools_json: Optional[List[dict]] = Field(default=None)
    allow_delegation: Optional[bool] = Field(default=None)
    max_execution_time: Optional[int] = Field(default=None, ge=10, le=600)
    is_enabled: Optional[int] = Field(default=None, ge=0, le=1)


class ExpertOut(CamelModel):
    """专家输出（独立实体，无 team_id）"""
    id: int
    member_name: str
    member_role: str
    avatar: str
    goal: str = ""
    backstory: str = ""
    system_prompt: str
    model_name: str
    provider_id: Optional[int] = None
    temperature: float = 0.7
    max_tokens: int
    tools_json: Optional[List[dict]] = None
    allow_delegation: int = 0
    max_execution_time: int = 120
    is_enabled: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── 专家团 ───────────────────────────────────────────────

class ExpertTeamCreate(CamelModel):
    """创建专家团"""
    team_name: str = Field(..., min_length=1, max_length=256, description="专家团名称")
    description: str = Field(default="", max_length=1024, description="描述")
    icon: str = Field(default="👥", description="图标 emoji 或 base64 小图")
    category: str = Field(default="通用", max_length=64, description="分类")
    leader_id: int = Field(default=0, ge=0, description="组长/PM 专家 ID (0=未设置)")
    orchestrator_prompt: str = Field(default="", description="编排器系统提示词")
    synthesizer_prompt: str = Field(default="", description="汇总器系统提示词")
    max_rounds: int = Field(default=3, ge=1, le=10, description="最大讨论轮次")
    process_mode: str = Field(default="parallel", description="执行模式: parallel=并行 sequential=顺序")
    config_json: Optional[dict] = Field(default=None, description="扩展配置")
    expert_ids: List[int] = Field(default=[], description="绑定的专家 ID 列表")


class ExpertTeamUpdate(CamelModel):
    """更新专家团"""
    team_name: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = Field(default=None, max_length=1024)
    icon: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None, max_length=64)
    leader_id: Optional[int] = Field(default=None, ge=0, description="组长/PM 专家 ID")
    orchestrator_prompt: Optional[str] = Field(default=None)
    synthesizer_prompt: Optional[str] = Field(default=None)
    max_rounds: Optional[int] = Field(default=None, ge=1, le=10)
    process_mode: Optional[str] = Field(default=None, description="执行模式")
    is_enabled: Optional[int] = Field(default=None, ge=0, le=1)
    config_json: Optional[dict] = Field(default=None)
    expert_ids: Optional[List[int]] = Field(default=None, description="绑定的专家 ID 列表（整体替换）")


class ExpertTeamBindExperts(CamelModel):
    """绑定专家到专家团"""
    expert_ids: List[int] = Field(..., description="要绑定的专家 ID 列表")


class ExpertTeamOut(CamelModel):
    """专家团输出"""
    id: int
    team_name: str
    description: str
    icon: str
    category: str
    leader_id: int = 0
    orchestrator_prompt: str
    synthesizer_prompt: str
    max_rounds: int
    process_mode: str = "parallel"
    is_enabled: int
    version: int
    config_json: Optional[dict] = None
    leader: Optional[ExpertOut] = None  # 组长/PM 专家详情
    experts: List[ExpertOut] = []  # 通过 binding 查询的专家列表
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


class PolishPromptRequest(CamelModel):
    """润色提示词请求"""
    content: str = Field(..., min_length=1, description="原始提示词内容")


# ─── 讨论消息 ─────────────────────────────────────────────

class DiscussionMessage(CamelModel):
    """讨论过程中的单条消息"""
    round: int = Field(..., description="轮次")
    expert_name: str = Field(..., description="专家名称")
    expert_role: str = Field(..., description="专家角色")
    content: str = Field(..., description="发言内容")
    timestamp: str = Field(..., description="时间戳")


# ─── 专家技能绑定 ─────────────────────────────────────────

class ExpertSkillCreate(CamelModel):
    """绑定技能到专家"""
    skill_id: int = Field(..., description="技能 ID")
    priority: int = Field(default=0, ge=0, description="调用优先级")
    config_override: Optional[dict] = Field(default=None, description="配置覆盖")
    is_enabled: int = Field(default=1, ge=0, le=1, description="是否启用")


class ExpertSkillUpdate(CamelModel):
    """更新专家技能绑定"""
    priority: Optional[int] = Field(default=None, ge=0)
    config_override: Optional[dict] = Field(default=None)
    is_enabled: Optional[int] = Field(default=None, ge=0, le=1)


class ExpertSkillOut(CamelModel):
    """专家技能绑定输出"""
    id: int
    expert_id: int
    skill_id: int
    skill_name: str = ""
    skill_display_name: str = ""
    skill_description: str = ""
    priority: int
    config_override: Optional[dict] = None
    is_enabled: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── 角色执行记录 ─────────────────────────────────────────

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
