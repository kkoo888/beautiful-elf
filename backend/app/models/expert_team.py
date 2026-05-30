"""专家团工作流模型"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, Text, Index
from app.models.base import BaseModel


class ExpertTeam(BaseModel):
    """专家团定义"""
    __tablename__ = "expert_teams"

    name = Column(String(256), nullable=False, comment="专家团名称")
    description = Column(String(1024), default="", comment="专家团描述")
    icon = Column(String(64), default="👥", comment="图标")
    category = Column(String(64), default="通用", comment="分类")
    orchestrator_prompt = Column(Text, default="", comment="编排器系统提示词")
    synthesizer_prompt = Column(Text, default="", comment="汇总器系统提示词")
    max_rounds = Column(Integer, default=3, comment="最大讨论轮次")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")
    version = Column(Integer, nullable=False, default=1, comment="版本号")
    config_json = Column(JSON, default=None, comment="扩展配置")

    __table_args__ = (
        Index("idx_expert_teams_enabled", "deleted", "enabled"),
        Index("idx_expert_teams_category", "category"),
    )


class ExpertTeamMember(BaseModel):
    """专家团成员"""
    __tablename__ = "expert_team_members"

    team_id = Column(BigInteger, nullable=False, comment="专家团 ID")
    name = Column(String(128), nullable=False, comment="专家名称")
    role = Column(String(128), nullable=False, comment="专家角色 (如: 架构师、测试专家)")
    avatar = Column(String(64), default="🤖", comment="头像 emoji")
    system_prompt = Column(Text, nullable=False, comment="专家系统提示词")
    model_name = Column(String(128), default="", comment="使用的模型名称")
    temperature = Column(Integer, default=70, comment="温度参数 (x100 存储)")
    max_tokens = Column(Integer, default=2048, comment="最大生成 token 数")
    tools_json = Column(JSON, default=None, comment="可用工具列表")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")

    __table_args__ = (
        Index("idx_expert_members_team", "team_id", "deleted"),
    )


class ExpertTeamRun(BaseModel):
    """专家团运行记录"""
    __tablename__ = "expert_team_runs"

    team_id = Column(BigInteger, nullable=False, comment="专家团 ID")
    status = Column(Integer, nullable=False, default=0, comment="状态: 0=待执行 1=运行中 2=已完成 3=失败 4=已取消")
    trigger_type = Column(Integer, nullable=False, default=0, comment="触发方式: 0=手动 1=定时 2=事件")
    input_text = Column(Text, default="", comment="用户输入")
    output_text = Column(Text, default="", comment="最终输出")
    discussion_json = Column(JSON, default=None, comment="讨论过程记录")
    error_message = Column(String(2048), default="", comment="错误信息")
    round_count = Column(Integer, default=0, comment="实际讨论轮次")
    token_usage = Column(Integer, default=0, comment="总 token 消耗")
    started_at = Column(DateTime, default=None, comment="开始时间")
    finished_at = Column(DateTime, default=None, comment="完成时间")
    duration_ms = Column(Integer, default=0, comment="执行耗时")

    __table_args__ = (
        Index("idx_expert_runs_team", "team_id", "status"),
        Index("idx_expert_runs_status", "status"),
        Index("idx_expert_runs_created", "created_at"),
    )


class ExpertRoleSkill(BaseModel):
    """角色技能绑定 — 专家成员可绑定已有技能，执行时按优先级调用"""
    __tablename__ = "expert_role_skills"

    role_id = Column(BigInteger, nullable=False, comment="成员 ID (关联 expert_team_members.id)")
    skill_id = Column(BigInteger, nullable=False, comment="技能 ID (关联 skills.id)")
    priority = Column(Integer, default=0, comment="调用优先级 (数值越大越优先)")
    config_override = Column(JSON, default=None, comment="角色级别的技能配置覆盖")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")

    __table_args__ = (
        Index("uk_role_skill", "role_id", "skill_id", unique=True),
        Index("idx_role_skills_role", "role_id"),
        Index("idx_role_skills_skill", "skill_id"),
    )


class ExpertRoleRun(BaseModel):
    """角色执行记录 — 每次运行中各专家成员的独立执行记录"""
    __tablename__ = "expert_role_runs"

    run_id = Column(BigInteger, nullable=False, comment="运行记录 ID (关联 expert_team_runs.id)")
    role_id = Column(BigInteger, nullable=False, comment="成员 ID (关联 expert_team_members.id)")
    role_name = Column(String(128), nullable=False, comment="成员名称 (冗余)")
    status = Column(Integer, nullable=False, default=0, comment="状态: 0=待运行 1=运行中 2=成功 3=失败 4=跳过")
    round_num = Column(Integer, default=0, comment="所在讨论轮次")
    input_json = Column(JSON, default=None, comment="角色输入 (子任务 + 上下文)")
    output_json = Column(JSON, default=None, comment="角色输出 (分析结果)")
    skills_used = Column(JSON, default=None, comment="实际调用的技能列表")
    error_message = Column(String(2048), default="", comment="错误信息")
    started_at = Column(DateTime, default=None, comment="开始时间")
    finished_at = Column(DateTime, default=None, comment="完成时间")
    duration_ms = Column(Integer, default=0, comment="执行耗时 (毫秒)")
    token_usage = Column(Integer, default=0, comment="token 消耗")

    __table_args__ = (
        Index("idx_role_runs_run", "run_id"),
        Index("idx_role_runs_role", "role_id"),
        Index("idx_role_runs_status", "status"),
    )
