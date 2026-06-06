"""专家团工作流模型"""
from sqlalchemy import Column, BigInteger, Integer, Float, String, DateTime, JSON, Text, Index
from app.models.base import BaseModel


class ExpertTeam(BaseModel):
    """专家团定义"""
    __tablename__ = "expert_team"

    team_name = Column(String(256), nullable=False, comment="专家团名称")
    description = Column(String(1024), default="", comment="专家团描述")
    icon = Column(String(64), default="👥", comment="图标")
    category = Column(String(64), default="通用", comment="分类")
    orchestrator_prompt = Column(Text, default="", comment="编排器系统提示词")
    synthesizer_prompt = Column(Text, default="", comment="汇总器系统提示词")
    max_rounds = Column(Integer, default=3, comment="最大讨论轮次")
    is_enabled = Column(Integer, nullable=False, default=1, comment="是否启用: 1=是 0=否")
    version = Column(Integer, nullable=False, default=1, comment="版本号")
    config_json = Column(JSON, default=None, comment="扩展配置")

    __table_args__ = (
        Index("idx_expert_team_is_deleted_enabled", "is_deleted", "is_enabled"),
        Index("idx_expert_team_category", "category"),
    )


class ExpertTeamMember(BaseModel):
    """专家团成员"""
    __tablename__ = "expert_team_member"

    team_id = Column(BigInteger, nullable=False, comment="专家团 ID")
    member_name = Column(String(128), nullable=False, comment="专家名称")
    member_role = Column(String(128), nullable=False, comment="专家角色 (如: 架构师、测试专家)")
    avatar = Column(String(64), default="🤖", comment="头像 emoji")
    system_prompt = Column(Text, nullable=False, comment="专家系统提示词")
    model_name = Column(String(128), default="", comment="使用的模型名称")
    provider_id = Column(BigInteger, default=None, nullable=True, comment="供应商 ID (关联 llm_model)")
    temperature = Column(Float, nullable=True, default=None, comment="温度覆盖 (为空则用模型默认温度)")
    max_tokens = Column(Integer, default=2048, comment="最大生成 token 数")
    tools_json = Column(JSON, default=None, comment="可用工具列表")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    is_enabled = Column(Integer, nullable=False, default=1, comment="是否启用: 1=是 0=否")

    __table_args__ = (
        Index("idx_expert_team_member_team_deleted", "team_id", "is_deleted"),
    )


class ExpertTeamRun(BaseModel):
    """专家团运行记录"""
    __tablename__ = "expert_team_run"

    team_id = Column(BigInteger, nullable=False, comment="专家团 ID")
    run_status = Column(Integer, nullable=False, default=0, comment="状态: 0=待执行 1=运行中 2=已完成 3=失败 4=已取消")
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
        Index("idx_expert_team_run_team_status", "team_id", "run_status"),
        Index("idx_expert_team_run_status", "run_status"),
        Index("idx_expert_team_run_created_at", "created_at"),
    )


class ExpertRoleSkill(BaseModel):
    """角色技能绑定 — 专家成员可绑定已有技能，执行时按优先级调用"""
    __tablename__ = "expert_role_skill"

    role_id = Column(BigInteger, nullable=False, comment="成员 ID (关联 expert_team_member.id)")
    skill_id = Column(BigInteger, nullable=False, comment="技能 ID (关联 skill.id)")
    priority = Column(Integer, default=0, comment="调用优先级 (数值越大越优先)")
    config_override = Column(JSON, default=None, comment="角色级别的技能配置覆盖")
    is_enabled = Column(Integer, nullable=False, default=1, comment="是否启用: 1=是 0=否")

    __table_args__ = (
        Index("uk_role_skill", "role_id", "skill_id", unique=True),
        Index("idx_expert_role_skill_skill_id", "skill_id"),
    )


class ExpertRoleRun(BaseModel):
    """角色执行记录 — 每次运行中各专家成员的独立执行记录"""
    __tablename__ = "expert_role_run"

    run_id = Column(BigInteger, nullable=False, comment="运行记录 ID (关联 expert_team_run.id)")
    role_id = Column(BigInteger, nullable=False, comment="成员 ID (关联 expert_team_member.id)")
    role_name = Column(String(128), nullable=False, comment="成员名称 (冗余)")
    run_status = Column(Integer, nullable=False, default=0, comment="状态: 0=待运行 1=运行中 2=成功 3=失败 4=跳过")
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
        Index("idx_expert_role_run_run_id", "run_id"),
        Index("idx_expert_role_run_role_id", "role_id"),
        Index("idx_expert_role_run_status", "run_status"),
    )
