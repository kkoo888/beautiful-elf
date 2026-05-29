"""SQLAlchemy ORM 模型 - 所有业务表"""
from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, DateTime,
    Numeric, JSON, func, UniqueConstraint, Index,
)
from app.models.base import BaseModel


# ============ 1. settings — 全局配置 ============
class Setting(BaseModel):
    __tablename__ = "settings"

    settings_key = Column(String(128), nullable=False, unique=True, comment="配置键")
    key_value = Column(Text, nullable=False, comment="配置值 (JSON)")
    description = Column(String(512), default="", comment="配置说明")
    restart_required = Column(Integer, nullable=False, default=0, comment="是否需要重启")

    __table_args__ = (
        Index("idx_settings_deleted", "deleted"),
    )


# ============ 2. conversations — 会话列表 ============
class Conversation(BaseModel):
    __tablename__ = "conversations"

    title = Column(String(256), nullable=False, default="", comment="会话标题")
    model_name = Column(String(128), default="", comment="对话模型")
    message_count = Column(Integer, nullable=False, default=0, comment="消息数量")
    last_message_at = Column(DateTime, default=None, comment="最后消息时间")

    __table_args__ = (
        Index("idx_conversations_created", "created_at"),
        Index("idx_conversations_last_msg", "last_message_at"),
        Index("idx_conversations_deleted", "deleted"),
    )


# ============ 3. messages — 消息记录 ============
class Message(BaseModel):
    __tablename__ = "messages"

    conversation_id = Column(BigInteger, nullable=False, comment="会话 ID")
    role = Column(String(32), nullable=False, comment="角色 (user/assistant/system/tool)")
    content = Column(Text, nullable=False, comment="消息内容")
    tool_calls = Column(JSON, default=None, comment="工具调用信息")
    tool_call_id = Column(String(128), default=None, comment="工具调用响应 ID")
    token_count = Column(Integer, default=0, comment="Token 消耗量")

    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id", "created_at"),
        Index("idx_messages_role", "role"),
    )


# ============ 4. memory_entries — 长期记忆 ============
class MemoryEntry(BaseModel):
    __tablename__ = "memory_entries"

    conversation_id = Column(BigInteger, default=None, comment="来源会话 ID")
    summary = Column(Text, nullable=False, comment="记忆摘要")
    tags = Column(JSON, default=None, comment="标签列表")
    importance = Column(Integer, nullable=False, default=5, comment="重要度 (1-10)")
    qdrant_point_id = Column(String(128), default=None, comment="Qdrant 向量 ID")

    __table_args__ = (
        Index("idx_memory_conversation", "conversation_id"),
        Index("idx_memory_importance", "importance"),
        Index("idx_memory_deleted", "deleted"),
    )


# ============ 5. knowledge_documents — 知识库文档 ============
class KnowledgeDocument(BaseModel):
    __tablename__ = "knowledge_documents"

    filename = Column(String(512), nullable=False, comment="文件名")
    file_type = Column(String(32), nullable=False, comment="文件类型")
    file_size = Column(BigInteger, nullable=False, default=0, comment="文件大小 (字节)")
    chunk_count = Column(Integer, nullable=False, default=0, comment="分块数量")
    status = Column(Integer, nullable=False, default=0, comment="处理状态 (0=待处理, 1=处理中, 2=完成, 3=失败)")
    error_message = Column(String(1024), default="", comment="失败原因")

    __table_args__ = (
        Index("idx_knowledge_type", "file_type"),
        Index("idx_knowledge_status", "status"),
        Index("idx_knowledge_deleted", "deleted"),
    )


# ============ 6. knowledge_chunks — 知识库分块索引 ============
class KnowledgeChunk(BaseModel):
    __tablename__ = "knowledge_chunks"

    document_id = Column(BigInteger, nullable=False, comment="文档 ID")
    chunk_index = Column(Integer, nullable=False, comment="分块序号")
    content_preview = Column(String(512), default="", comment="内容预览")
    qdrant_point_id = Column(String(128), nullable=False, comment="Qdrant 向量 ID")

    __table_args__ = (
        Index("idx_chunks_document", "document_id", "chunk_index"),
        Index("idx_chunks_qdrant", "qdrant_point_id"),
    )


# ============ 7. intents — 意图配置 ============
class Intent(BaseModel):
    __tablename__ = "intents"

    name = Column(String(128), nullable=False, comment="意图名称")
    description = Column(String(512), default="", comment="意图描述")
    trigger_texts = Column(JSON, nullable=False, comment="触发词列表")
    target_module = Column(String(128), nullable=False, comment="目标模块")
    metadata_ = Column("metadata", JSON, default=None, comment="扩展元数据")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")
    qdrant_point_id = Column(String(128), default=None, comment="Qdrant 向量 ID")

    __table_args__ = (
        Index("idx_intents_enabled", "deleted", "enabled"),
        Index("idx_intents_module", "target_module"),
    )


# ============ 8. intent_usage — 意图命中统计 ============
class IntentUsage(BaseModel):
    __tablename__ = "intent_usage"

    intent_id = Column(BigInteger, nullable=False, comment="意图 ID")
    hit_count = Column(Integer, nullable=False, default=0, comment="命中次数")
    avg_confidence = Column(Numeric(5, 4), nullable=False, default=0.0, comment="平均置信度")
    last_hit_at = Column(DateTime, default=None, comment="最后命中时间")

    __table_args__ = (
        Index("idx_usage_intent", "intent_id"),
        Index("idx_usage_hit_count", "hit_count"),
    )


# ============ 9. skills — 技能注册 ============
class Skill(BaseModel):
    __tablename__ = "skills"

    name = Column(String(128), nullable=False, unique=True, comment="技能名称")
    display_name = Column(String(256), default="", comment="显示名称")
    description = Column(String(1024), default="", comment="技能描述")
    version = Column(String(32), default="1.0.0", comment="版本号")
    source = Column(String(256), default="", comment="来源")
    trigger_words = Column(JSON, default=None, comment="触发词列表")
    dependencies = Column(JSON, default=None, comment="依赖技能列表")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")
    config = Column(JSON, default=None, comment="技能配置")

    __table_args__ = (
        Index("idx_skills_enabled", "deleted", "enabled"),
    )


# ============ 10. skill_stats — 技能使用统计 ============
class SkillStats(BaseModel):
    __tablename__ = "skill_stats"

    skill_id = Column(BigInteger, nullable=False, comment="技能 ID")
    call_count = Column(Integer, nullable=False, default=0, comment="调用次数")
    success_count = Column(Integer, nullable=False, default=0, comment="成功次数")
    fail_count = Column(Integer, nullable=False, default=0, comment="失败次数")
    avg_duration_ms = Column(Integer, nullable=False, default=0, comment="平均耗时")
    last_called_at = Column(DateTime, default=None, comment="最后调用时间")

    __table_args__ = (
        Index("idx_skill_stats_skill", "skill_id"),
        Index("idx_skill_stats_calls", "call_count"),
    )


# ============ 11. workflows — 工作流定义 ============
class Workflow(BaseModel):
    __tablename__ = "workflows"

    name = Column(String(256), nullable=False, comment="工作流名称")
    description = Column(String(1024), default="", comment="工作流描述")
    dag_json = Column(JSON, nullable=False, comment="DAG 定义")
    trigger_type = Column(Integer, nullable=False, default=0, comment="触发方式")
    cron_expr = Column(String(64), default="", comment="cron 表达式")
    event_trigger = Column(String(256), default="", comment="事件触发条件")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")
    version = Column(Integer, nullable=False, default=1, comment="版本号")

    __table_args__ = (
        Index("idx_workflows_enabled", "deleted", "enabled"),
        Index("idx_workflows_trigger", "trigger_type"),
    )


# ============ 12. workflow_runs — 工作流运行记录 ============
class WorkflowRun(BaseModel):
    __tablename__ = "workflow_runs"

    workflow_id = Column(BigInteger, nullable=False, comment="工作流 ID")
    status = Column(Integer, nullable=False, default=0, comment="状态")
    trigger_type = Column(Integer, nullable=False, default=0, comment="触发方式")
    input_json = Column(JSON, default=None, comment="输入参数")
    output_json = Column(JSON, default=None, comment="输出结果")
    error_message = Column(String(2048), default="", comment="错误信息")
    started_at = Column(DateTime, default=None, comment="开始时间")
    finished_at = Column(DateTime, default=None, comment="完成时间")
    duration_ms = Column(Integer, default=0, comment="执行耗时")

    __table_args__ = (
        Index("idx_wf_runs_workflow", "workflow_id", "status"),
        Index("idx_wf_runs_status", "status"),
        Index("idx_wf_runs_created", "created_at"),
    )


# ============ 13. workflow_step_runs — 节点执行详情 ============
class WorkflowStepRun(BaseModel):
    __tablename__ = "workflow_step_runs"

    run_id = Column(BigInteger, nullable=False, comment="运行记录 ID")
    step_name = Column(String(128), nullable=False, comment="节点名称")
    step_type = Column(String(64), nullable=False, comment="节点类型")
    status = Column(Integer, nullable=False, default=0, comment="状态")
    input_json = Column(JSON, default=None, comment="输入数据")
    output_json = Column(JSON, default=None, comment="输出数据")
    error_message = Column(String(2048), default="", comment="错误信息")
    started_at = Column(DateTime, default=None, comment="开始时间")
    finished_at = Column(DateTime, default=None, comment="完成时间")
    duration_ms = Column(Integer, default=0, comment="执行耗时")

    __table_args__ = (
        Index("idx_step_runs_run", "run_id", "step_name"),
        Index("idx_step_runs_status", "status"),
    )


# ============ 14. tools — 工具注册表 ============
class Tool(BaseModel):
    __tablename__ = "tools"

    name = Column(String(128), nullable=False, unique=True, comment="工具名称")
    display_name = Column(String(256), default="", comment="显示名称")
    description = Column(String(1024), nullable=False, comment="工具描述")
    module = Column(String(128), nullable=False, comment="所属模块")
    json_schema = Column(JSON, nullable=False, comment="参数 JSON Schema")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")

    __table_args__ = (
        Index("idx_tools_module", "module"),
        Index("idx_tools_enabled", "deleted", "enabled"),
    )


# ============ 15. tool_stats — 工具调用统计 ============
class ToolStats(BaseModel):
    __tablename__ = "tool_stats"

    tool_id = Column(BigInteger, nullable=False, comment="工具 ID")
    call_count = Column(Integer, nullable=False, default=0, comment="调用次数")
    success_count = Column(Integer, nullable=False, default=0, comment="成功次数")
    fail_count = Column(Integer, nullable=False, default=0, comment="失败次数")
    avg_duration_ms = Column(Integer, nullable=False, default=0, comment="平均耗时")
    last_called_at = Column(DateTime, default=None, comment="最后调用时间")

    __table_args__ = (
        Index("idx_tool_stats_tool", "tool_id"),
        Index("idx_tool_stats_calls", "call_count"),
    )


# ============ 16. schedules — 日程事件 ============
class Schedule(BaseModel):
    __tablename__ = "schedules"

    title = Column(String(256), nullable=False, comment="日程标题")
    description = Column(String(2048), default="", comment="日程描述")
    start_time = Column(DateTime, nullable=False, comment="开始时间")
    end_time = Column(DateTime, default=None, comment="结束时间")
    all_day = Column(Integer, nullable=False, default=0, comment="是否全天事件")
    reminder_minutes = Column(Integer, default=0, comment="提前提醒时间 (分钟)")
    reminded = Column(Integer, nullable=False, default=0, comment="是否已提醒")
    repeat_type = Column(Integer, nullable=False, default=0, comment="重复类型")
    color = Column(String(16), default="", comment="颜色标记")

    __table_args__ = (
        Index("idx_schedules_start", "start_time"),
        Index("idx_schedules_reminder", "reminded", "reminder_minutes", "start_time"),
        Index("idx_schedules_deleted", "deleted"),
    )


# ============ 17. clipboard_items — 剪贴板历史 ============
class ClipboardItem(BaseModel):
    __tablename__ = "clipboard_items"

    content = Column(Text, nullable=False, comment="剪贴板内容")
    content_type = Column(Integer, nullable=False, default=0, comment="内容类型")
    pinned = Column(Integer, nullable=False, default=0, comment="是否固定")
    source_app = Column(String(256), default="", comment="来源应用")

    __table_args__ = (
        Index("idx_clipboard_pinned", "pinned"),
        Index("idx_clipboard_type", "content_type"),
        Index("idx_clipboard_created", "created_at"),
    )


# ============ 18. snippets — 代码片段 ============
class Snippet(BaseModel):
    __tablename__ = "snippets"

    title = Column(String(256), nullable=False, comment="片段标题")
    content = Column(Text, nullable=False, comment="代码内容")
    language = Column(String(64), default="", comment="编程语言")
    use_count = Column(Integer, nullable=False, default=0, comment="使用次数")

    __table_args__ = (
        Index("idx_snippets_language", "language"),
        Index("idx_snippets_use_count", "use_count"),
        Index("idx_snippets_deleted", "deleted"),
    )


# ============ 18.1 snippet_tags — 代码片段标签 ============
class SnippetTag(BaseModel):
    __tablename__ = "snippet_tags"

    snippet_id = Column(BigInteger, nullable=False, comment="片段 ID")
    tag = Column(String(64), nullable=False, comment="标签名称")

    __table_args__ = (
        UniqueConstraint("snippet_id", "tag", name="uk_snippet_tag"),
        Index("idx_snippet_tags_tag", "tag"),
    )


# ============ 19. pet_attributes — 宠物属性（单例） ============
class PetAttribute(BaseModel):
    __tablename__ = "pet_attributes"

    hunger = Column(Integer, nullable=False, default=100, comment="饥饿值 (0-100)")
    clean = Column(Integer, nullable=False, default=100, comment="清洁值 (0-100)")
    mood = Column(Integer, nullable=False, default=100, comment="心情值 (0-100)")
    health = Column(Integer, nullable=False, default=100, comment="健康值 (0-100)")
    intimacy = Column(Integer, nullable=False, default=0, comment="亲密度")
    level = Column(Integer, nullable=False, default=1, comment="等级")
    exp = Column(Integer, nullable=False, default=0, comment="经验值")
    last_active_at = Column(DateTime, nullable=False, server_default=func.now(), comment="最后活跃时间")


# ============ 20. pet_interactions — 互动记录 ============
class PetInteraction(BaseModel):
    __tablename__ = "pet_interactions"

    pet_attribute_id = Column(BigInteger, nullable=False, comment="宠物属性 ID")
    interaction_type = Column(Integer, nullable=False, comment="互动类型")
    effect_json = Column(JSON, default=None, comment="属性变化效果")

    __table_args__ = (
        Index("idx_pet_interactions_type", "interaction_type"),
        Index("idx_pet_interactions_created", "created_at"),
    )


# ============ 21. action_logs — 行为日志 ============
class ActionLog(BaseModel):
    __tablename__ = "action_logs"

    module = Column(String(64), nullable=False, comment="模块名")
    action = Column(String(128), nullable=False, comment="行为动作")
    params_summary = Column(String(512), default="", comment="参数摘要 (已脱敏)")
    session_id = Column(String(128), default="", comment="会话 ID")

    __table_args__ = (
        Index("idx_action_logs_module", "module"),
        Index("idx_action_logs_created", "created_at"),
        Index("idx_action_logs_action", "action"),
    )


# ============ 22. commands — 命令注册 ============
class Command(BaseModel):
    __tablename__ = "commands"

    name = Column(String(128), nullable=False, unique=True, comment="命令名称")
    display_name = Column(String(256), default="", comment="显示名称")
    description = Column(String(512), default="", comment="命令描述")
    shortcut_key = Column(String(32), default="", comment="快捷键")
    module = Column(String(64), nullable=False, comment="所属模块")
    command_type = Column(Integer, nullable=False, default=0, comment="类型")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")

    __table_args__ = (
        Index("idx_commands_module", "module"),
        Index("idx_commands_enabled", "deleted", "enabled"),
    )


# ============ 23. command_usage — 命令使用频率 ============
class CommandUsage(BaseModel):
    __tablename__ = "command_usage"

    command_id = Column(BigInteger, nullable=False, comment="命令 ID")
    use_count = Column(Integer, nullable=False, default=0, comment="使用次数")
    last_used_at = Column(DateTime, default=None, comment="最后使用时间")

    __table_args__ = (
        Index("idx_command_usage_cmd", "command_id"),
        Index("idx_command_usage_count", "use_count"),
    )


# ============ 24. performance_metrics — 性能采样 ============
class PerformanceMetric(BaseModel):
    __tablename__ = "performance_metrics"

    cpu_percent = Column(Numeric(5, 2), nullable=False, default=0.0, comment="CPU 使用率")
    memory_percent = Column(Numeric(5, 2), nullable=False, default=0.0, comment="内存使用率")
    memory_used_mb = Column(Integer, nullable=False, default=0, comment="已用内存 (MB)")
    disk_percent = Column(Numeric(5, 2), nullable=False, default=0.0, comment="磁盘使用率")
    disk_used_gb = Column(Integer, nullable=False, default=0, comment="已用磁盘 (GB)")
    gpu_percent = Column(Numeric(5, 2), default=None, comment="GPU 使用率")

    __table_args__ = (
        Index("idx_perf_created", "created_at"),
    )


# ============ 25. soul_configs — 助手人格配置 ============
class SoulConfig(BaseModel):
    __tablename__ = "soul_configs"

    name = Column(String(128), nullable=False, comment="助手名称")
    avatar_url = Column(String(512), default="", comment="头像地址")
    personality = Column(JSON, nullable=False, comment="性格标签")
    speaking_style = Column(String(256), default="", comment="说话风格")
    background = Column(Text, default=None, comment="背景故事")
    system_prompt = Column(Text, nullable=False, comment="系统提示词")
    is_active = Column(Integer, nullable=False, default=1, comment="是否激活")

    __table_args__ = (
        Index("idx_soul_active", "is_active"),
    )


# ============ 26. backup_records — 备份记录 ============
class BackupRecord(BaseModel):
    __tablename__ = "backup_records"

    backup_type = Column(Integer, nullable=False, comment="备份类型")
    file_path = Column(String(512), nullable=False, comment="备份文件路径")
    file_size = Column(BigInteger, nullable=False, default=0, comment="文件大小")
    status = Column(Integer, nullable=False, default=0, comment="状态")
    error_message = Column(String(1024), default="", comment="失败原因")

    __table_args__ = (
        Index("idx_backup_type", "backup_type"),
        Index("idx_backup_status", "status"),
        Index("idx_backup_created", "created_at"),
    )


# ============ 27. prompts — Prompt 版本管理 ============
class Prompt(BaseModel):
    __tablename__ = "prompts"

    name = Column(String(128), nullable=False, comment="Prompt 名称")
    content = Column(Text, nullable=False, comment="Prompt 内容")
    version = Column(Integer, nullable=False, default=1, comment="版本号")
    is_active = Column(Integer, nullable=False, default=0, comment="是否激活")
    description = Column(String(512), default="", comment="版本说明")

    __table_args__ = (
        Index("idx_prompts_name", "name", "version"),
        Index("idx_prompts_active", "name", "is_active"),
    )


# ============ 28. ai_feedback — AI 回答反馈 ============
class AIFeedback(BaseModel):
    __tablename__ = "ai_feedback"

    conversation_id = Column(BigInteger, default=None, comment="会话 ID")
    question = Column(Text, nullable=False, comment="用户问题")
    answer = Column(Text, nullable=False, comment="AI 回答")
    feedback_type = Column(Integer, nullable=False, comment="反馈类型")
    reason_tags = Column(JSON, default=None, comment="原因标签")
    reason_text = Column(String(2048), default="", comment="自由文本")
    trace_id = Column(String(128), default="", comment="请求链路 ID")

    __table_args__ = (
        Index("idx_feedback_type", "feedback_type"),
        Index("idx_feedback_conversation", "conversation_id"),
        Index("idx_feedback_created", "created_at"),
    )


# ============ 29. notifications — 通知历史 ============
class Notification(BaseModel):
    __tablename__ = "notifications"

    event_id = Column(String(128), default="", comment="事件去重 ID")
    type = Column(String(32), nullable=False, comment="通知类型")
    title = Column(String(256), nullable=False, comment="通知标题")
    message = Column(Text, nullable=False, comment="通知内容")
    read = Column(Integer, nullable=False, default=0, comment="是否已读")
    action_url = Column(String(512), default="", comment="跳转地址")

    __table_args__ = (
        Index("idx_notifications_type", "type"),
        Index("idx_notifications_read", "read"),
        Index("idx_notifications_created", "created_at"),
    )
