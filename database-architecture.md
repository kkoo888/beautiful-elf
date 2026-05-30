# Beautiful-Elf 数据库关系图

## 📐 存储分层总览

| 存储引擎 | 职责 | 数据类型 |
|----------|------|---------|
| MySQL 9.5 | 业务数据唯一真相源 | 所有 CRUD 业务数据 |
| Redis 8.6 | 缓存 + 消息代理 | 热数据缓存、Celery Broker、WebSocket 队列 |
| Qdrant | AI 向量专用 | intent_vectors、knowledge_chunks、memory_vectors |

**Qdrant Collections**:

| Collection | 向量来源 | payload 字段 | 关联 MySQL 表 |
|-----------|---------|-------------|--------------|
| `intent_vectors` | intents.trigger_texts → Qwen3-Embedding | `{ intent_id, deleted }` | intents |
| `knowledge_chunks` | 文档分块 → Qwen3-Embedding | `{ doc_id, chunk_index, deleted }` | knowledge_documents + knowledge_chunks |
| `memory_vectors` | memory_entries.summary → Qwen3-Embedding | `{ memory_id, deleted }` | memory_entries |

**关联方式**: MySQL 与 Qdrant 通过 ID 关联，查询时先检索 Qdrant 获取向量匹配结果（含 payload 中的业务 ID），再用 ID 去 MySQL 查询完整业务数据。

**外键策略**: 数据库层不建外键约束（`FOREIGN KEY`），由应用层 Repository 保证引用完整性。原因：① InnoDB 外键有性能开销 ② 批量导入/迁移时外键会阻塞 ③ 软删除场景下外键约束不适用。应用层必须确保：写入前校验关联 ID 存在，删除时级联处理关联数据。

---

## 🗂️ 通用字段约定

> 所有业务表必须包含以下字段，遵循 P3C 规范。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PRIMARY KEY AUTO_INCREMENT | 主键 |
| deleted | TINYINT | NOT NULL DEFAULT 0 | 软删除标记 (0=正常, 1=已删除) |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**命名规约**:
- 表名: snake_case，复数形式 (schedules, pet_attributes)
- 字段名: snake_case (created_at, reminder_time)
- 索引名: idx_table_field (idx_messages_conversation_id)
- 唯一索引: uk_table_field (uk_settings_key)
- 字符集: UTF-8MB4

**JSON 字段使用原则**:
- [推荐] 高频查询/过滤/聚合的字段应拆独立表，不用 JSON
- [允许] 低频读取、结构灵活、不需要索引的配置类数据可用 JSON
- 当前使用 JSON 的字段评估:
  - `intents.trigger_texts` → 允许（触发词列表，低频更新，不需单独查询）
  - `messages.tool_calls` → 允许（工具调用记录，只读，不需索引）
  - `workflows.dag_json` → 允许（DAG 定义整体读写，不拆分查询）
  - `tools.json_schema` → 允许（Schema 整体使用，不需索引内部字段）
  - `soul_configs.personality` → 允许（配置数据，低频读取）
  - `memory_entries.tags` → 允许（标签列表，低频更新，不需单独查询）

**TEXT 字段长度预警**:
- [推荐] TEXT 字段在应用层设置软上限（如 content 最大 100KB）
- [推荐] 超长文本写入时记录日志告警
- [推荐] 前端展示时做截断处理（如列表页只显示前 200 字）

---

## 📊 表结构详细定义

### 1. settings — 全局配置

> 所有业务配置统一存此表，不使用 .env 文件。KV 结构。

```sql
CREATE TABLE settings (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    settings_key    VARCHAR(128)    NOT NULL COMMENT '配置键',
    key_value       TEXT            NOT NULL COMMENT '配置值 (JSON 字符串)',
    description     VARCHAR(512)    DEFAULT '' COMMENT '配置说明',
    restart_required TINYINT        NOT NULL DEFAULT 0 COMMENT '是否需要重启 (0=否, 1=是)',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_settings_key (settings_key),
    INDEX idx_settings_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='全局配置表';
```

### 2. conversations — 会话列表

```sql
CREATE TABLE conversations (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(256)    NOT NULL DEFAULT '' COMMENT '会话标题',
    model_name      VARCHAR(128)    DEFAULT '' COMMENT '使用的对话模型',
    message_count   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '消息数量',
    last_message_at DATETIME        DEFAULT NULL COMMENT '最后消息时间',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_conversations_created (created_at),
    INDEX idx_conversations_last_msg (last_message_at),
    INDEX idx_conversations_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会话列表';
```

### 3. messages — 消息记录

> 原始对话历史，完整保留，不向量化。

```sql
CREATE TABLE messages (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED NOT NULL COMMENT '所属会话 ID',
    role            VARCHAR(32)     NOT NULL COMMENT '角色 (user/assistant/system/tool)',
    content         TEXT            NOT NULL COMMENT '消息内容 (应用层软上限 100KB)',
    tool_calls      JSON            DEFAULT NULL COMMENT '工具调用信息 (assistant 角色)',
    tool_call_id    VARCHAR(128)    DEFAULT NULL COMMENT '工具调用响应 ID (tool 角色)',
    token_count     INT UNSIGNED    DEFAULT 0 COMMENT 'Token 消耗量',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_messages_conversation (conversation_id, created_at),
    INDEX idx_messages_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息记录';
```

### 4. memory_entries — 长期记忆

> 从对话中提炼的摘要和关键信息，非原始消息。

```sql
CREATE TABLE memory_entries (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED DEFAULT NULL COMMENT '来源会话 ID (应用层校验存在性)',
    summary         VARCHAR(512)    NOT NULL COMMENT '记忆摘要 (简短描述)',
    content         TEXT            NOT NULL COMMENT '记忆详细内容 (应用层软上限 10KB)',
    tags            JSON            DEFAULT NULL COMMENT '标签列表',
    importance      TINYINT UNSIGNED NOT NULL DEFAULT 5 COMMENT '重要度 (1-10)',
    qdrant_point_id VARCHAR(128)    DEFAULT NULL COMMENT 'Qdrant 中的向量 ID',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_memory_conversation (conversation_id),
    INDEX idx_memory_importance (importance),
    INDEX idx_memory_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='长期记忆';
```

### 5. knowledge_documents — 知识库文档元数据

```sql
CREATE TABLE knowledge_documents (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    filename        VARCHAR(512)    NOT NULL COMMENT '文件名',
    file_type       VARCHAR(32)     NOT NULL COMMENT '文件类型 (pdf/docx/md/txt/json/csv/yaml/html/xml/zip)',
    file_size       BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '文件大小 (字节)',
    chunk_count     INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '分块数量',
    status          TINYINT         NOT NULL DEFAULT 0 COMMENT '处理状态 (0=待处理, 1=处理中, 2=完成, 3=失败)',
    error_message   VARCHAR(1024)   DEFAULT '' COMMENT '失败原因',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_knowledge_type (file_type),
    INDEX idx_knowledge_status (status),
    INDEX idx_knowledge_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档元数据';
```

### 6. knowledge_chunks — 知识库文档分块索引

> 记录 Qdrant 中的向量 ID 映射。

```sql
CREATE TABLE knowledge_chunks (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    document_id     BIGINT UNSIGNED NOT NULL COMMENT '所属文档 ID (应用层校验存在性)',
    chunk_index     INT UNSIGNED    NOT NULL COMMENT '分块序号',
    content_preview VARCHAR(512)    DEFAULT '' COMMENT '内容预览 (前 200 字)',
    qdrant_point_id VARCHAR(128)    NOT NULL COMMENT 'Qdrant 中的向量 ID',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_chunks_document (document_id, chunk_index),
    INDEX idx_chunks_qdrant (qdrant_point_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档分块索引';
```

### 7. intents — 意图配置

> 文本 + 触发词 + 目标模块 + 元数据。

```sql
CREATE TABLE intents (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '意图名称',
    description     VARCHAR(512)    DEFAULT '' COMMENT '意图描述',
    trigger_texts   JSON            NOT NULL COMMENT '触发词列表 (低频更新，不需单独查询)',
    target_module   VARCHAR(128)    NOT NULL COMMENT '目标模块/工具名',
    metadata        JSON            DEFAULT NULL COMMENT '扩展元数据',
    enabled         TINYINT         NOT NULL DEFAULT 1 COMMENT '是否启用 (0=禁用, 1=启用)',
    qdrant_point_id VARCHAR(128)    DEFAULT NULL COMMENT 'Qdrant 中的向量 ID',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_intents_enabled (deleted, enabled),
    INDEX idx_intents_module (target_module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='意图配置';
```

### 8. intent_usage — 意图命中统计

```sql
CREATE TABLE intent_usage (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    intent_id       BIGINT UNSIGNED NOT NULL COMMENT '意图 ID (应用层校验存在性)',
    hit_count       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '命中次数',
    avg_confidence  DECIMAL(5,4)    NOT NULL DEFAULT 0.0000 COMMENT '平均置信度',
    last_hit_at     DATETIME        DEFAULT NULL COMMENT '最后命中时间',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_usage_intent (intent_id),
    INDEX idx_usage_hit_count (hit_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='意图命中统计';
```

### 9. skills — 技能注册

```sql
CREATE TABLE skills (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '技能名称',
    display_name    VARCHAR(256)    DEFAULT '' COMMENT '显示名称',
    description     VARCHAR(1024)   DEFAULT '' COMMENT '技能描述',
    version         VARCHAR(32)     DEFAULT '1.0.0' COMMENT '版本号',
    source          VARCHAR(256)    DEFAULT '' COMMENT '来源 (GitHub URL / local)',
    trigger_words   JSON            DEFAULT NULL COMMENT '触发词列表',
    dependencies    JSON            DEFAULT NULL COMMENT '依赖技能列表',
    enabled         TINYINT         NOT NULL DEFAULT 1 COMMENT '是否启用',
    config          JSON            DEFAULT NULL COMMENT '技能配置',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_skills_name (name),
    INDEX idx_skills_enabled (deleted, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能注册表';
```

### 10. skill_stats — 技能使用统计

> 仅用于日志展示和优化建议，不限流。

```sql
CREATE TABLE skill_stats (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    skill_id        BIGINT UNSIGNED NOT NULL COMMENT '技能 ID (应用层校验存在性)',
    call_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '调用次数',
    success_count   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '成功次数',
    fail_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '失败次数',
    avg_duration_ms INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '平均耗时 (毫秒)',
    last_called_at  DATETIME        DEFAULT NULL COMMENT '最后调用时间',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_skill_stats_skill (skill_id),
    INDEX idx_skill_stats_calls (call_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能使用统计';
```

### 11. workflows — 工作流定义

```sql
CREATE TABLE workflows (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(256)    NOT NULL COMMENT '工作流名称',
    description     VARCHAR(1024)   DEFAULT '' COMMENT '工作流描述',
    dag_json        JSON            NOT NULL COMMENT 'LangGraph DAG 定义 (节点+边，整体读写)',
    trigger_type    TINYINT         NOT NULL DEFAULT 0 COMMENT '触发方式 (0=手动, 1=定时, 2=事件)',
    cron_expr       VARCHAR(64)     DEFAULT '' COMMENT '定时触发 cron 表达式',
    event_trigger   VARCHAR(256)    DEFAULT '' COMMENT '事件触发条件',
    enabled         TINYINT         NOT NULL DEFAULT 1 COMMENT '是否启用',
    version         INT UNSIGNED    NOT NULL DEFAULT 1 COMMENT '版本号',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_workflows_enabled (deleted, enabled),
    INDEX idx_workflows_trigger (trigger_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流定义';
```

### 12. workflow_runs — 工作流运行记录

```sql
CREATE TABLE workflow_runs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    workflow_id     BIGINT UNSIGNED NOT NULL COMMENT '工作流 ID (应用层校验存在性)',
    status          TINYINT         NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=成功, 3=失败, 4=已取消)',
    trigger_type    TINYINT         NOT NULL DEFAULT 0 COMMENT '触发方式 (0=手动, 1=定时, 2=事件)',
    input_json      JSON            DEFAULT NULL COMMENT '输入参数',
    output_json     JSON            DEFAULT NULL COMMENT '输出结果',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    started_at      DATETIME        DEFAULT NULL COMMENT '开始时间',
    finished_at     DATETIME        DEFAULT NULL COMMENT '结束时间',
    duration_ms     INT UNSIGNED    DEFAULT 0 COMMENT '执行耗时 (毫秒)',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_wf_runs_workflow (workflow_id, status),
    INDEX idx_wf_runs_status (status),
    INDEX idx_wf_runs_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流运行记录';
```

### 13. workflow_step_runs — 节点执行详情

```sql
CREATE TABLE workflow_step_runs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    run_id          BIGINT UNSIGNED NOT NULL COMMENT '运行记录 ID (应用层校验存在性)',
    step_name       VARCHAR(128)    NOT NULL COMMENT '节点名称',
    step_type       VARCHAR(64)     NOT NULL COMMENT '节点类型 (tool/skill/subagent/llm)',
    status          TINYINT         NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=成功, 3=失败, 4=跳过)',
    input_json      JSON            DEFAULT NULL COMMENT '输入数据',
    output_json     JSON            DEFAULT NULL COMMENT '输出数据',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    started_at      DATETIME        DEFAULT NULL COMMENT '开始时间',
    finished_at     DATETIME        DEFAULT NULL COMMENT '结束时间',
    duration_ms     INT UNSIGNED    DEFAULT 0 COMMENT '执行耗时 (毫秒)',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_step_runs_run (run_id, step_name),
    INDEX idx_step_runs_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流节点执行详情';
```

### 14. tools — 工具注册表

```sql
CREATE TABLE tools (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '工具名称',
    display_name    VARCHAR(256)    DEFAULT '' COMMENT '显示名称',
    description     VARCHAR(1024)   NOT NULL COMMENT '工具描述',
    module          VARCHAR(128)    NOT NULL COMMENT '所属模块',
    json_schema     JSON            NOT NULL COMMENT '参数 JSON Schema (Schema 整体使用，不拆分)',
    enabled         TINYINT         NOT NULL DEFAULT 1 COMMENT '是否启用',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tools_name (name),
    INDEX idx_tools_module (module),
    INDEX idx_tools_enabled (deleted, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工具注册表';
```

### 15. tool_stats — 工具调用统计

> 仅用于日志展示，不限流。

```sql
CREATE TABLE tool_stats (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tool_id         BIGINT UNSIGNED NOT NULL COMMENT '工具 ID (应用层校验存在性)',
    call_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '调用次数',
    success_count   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '成功次数',
    fail_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '失败次数',
    avg_duration_ms INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '平均耗时 (毫秒)',
    last_called_at  DATETIME        DEFAULT NULL COMMENT '最后调用时间',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tool_stats_tool (tool_id),
    INDEX idx_tool_stats_calls (call_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工具调用统计';
```

### 16. schedules — 日程事件

```sql
CREATE TABLE schedules (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(256)    NOT NULL COMMENT '日程标题',
    description     VARCHAR(2048)   DEFAULT '' COMMENT '日程描述',
    location        VARCHAR(512)    DEFAULT '' COMMENT '地点',
    start_time      DATETIME        NOT NULL COMMENT '开始时间',
    end_time        DATETIME        DEFAULT NULL COMMENT '结束时间 (全天事件可为空)',
    all_day         TINYINT         NOT NULL DEFAULT 0 COMMENT '是否全天事件',
    reminder_minutes INT UNSIGNED   DEFAULT 0 COMMENT '提前提醒时间 (分钟)',
    reminded        TINYINT         NOT NULL DEFAULT 0 COMMENT '是否已提醒 (0=否, 1=是)',
    repeat_type     TINYINT         NOT NULL DEFAULT 0 COMMENT '重复类型 (0=不重复, 1=每天, 2=每周, 3=每月, 4=每年)',
    color           VARCHAR(16)     DEFAULT '' COMMENT '日历颜色标记',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_schedules_start (start_time),
    INDEX idx_schedules_reminder (reminded, reminder_minutes, start_time),
    INDEX idx_schedules_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日程事件';
```

### 17. clipboard_items — 剪贴板历史

```sql
CREATE TABLE clipboard_items (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    content         TEXT            NOT NULL COMMENT '剪贴板内容 (应用层软上限 100KB)',
    content_type    TINYINT         NOT NULL DEFAULT 0 COMMENT '内容类型 (0=文本, 1=代码, 2=图片, 3=链接, 4=文件路径)',
    pinned          TINYINT         NOT NULL DEFAULT 0 COMMENT '是否固定',
    source_app      VARCHAR(256)    DEFAULT '' COMMENT '来源应用',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_clipboard_pinned (pinned),
    INDEX idx_clipboard_type (content_type),
    INDEX idx_clipboard_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='剪贴板历史';
```

### 18. snippets — 代码片段

```sql
CREATE TABLE snippets (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(256)    NOT NULL COMMENT '片段标题',
    content         TEXT            NOT NULL COMMENT '代码内容 (应用层软上限 50KB)',
    language        VARCHAR(64)     DEFAULT '' COMMENT '编程语言',
    use_count       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '使用次数',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_snippets_language (language),
    INDEX idx_snippets_use_count (use_count),
    INDEX idx_snippets_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='代码片段';
```

### 19. snippet_tags — 代码片段标签

> 标签独立存储，支持按标签高效搜索和聚合统计。

```sql
CREATE TABLE snippet_tags (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    snippet_id      BIGINT UNSIGNED NOT NULL COMMENT '片段 ID (应用层校验存在性)',
    tag             VARCHAR(64)     NOT NULL COMMENT '标签名称',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_snippet_tag (snippet_id, tag),
    INDEX idx_snippet_tags_tag (tag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='代码片段标签';
```

### 20. pet_attributes — 宠物属性（单例表）

> 全局只有一只宠物，此表始终只有一行数据。应用层启动时自动初始化。

```sql
CREATE TABLE pet_attributes (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    hunger          TINYINT UNSIGNED NOT NULL DEFAULT 100 COMMENT '饥饿值 (0-100)',
    clean           TINYINT UNSIGNED NOT NULL DEFAULT 100 COMMENT '清洁值 (0-100)',
    mood            TINYINT UNSIGNED NOT NULL DEFAULT 100 COMMENT '心情值 (0-100)',
    health          TINYINT UNSIGNED NOT NULL DEFAULT 100 COMMENT '健康值 (0-100)',
    intimacy        INT UNSIGNED     NOT NULL DEFAULT 0 COMMENT '亲密度',
    level           INT UNSIGNED     NOT NULL DEFAULT 1 COMMENT '等级',
    exp             INT UNSIGNED     NOT NULL DEFAULT 0 COMMENT '经验值',
    last_active_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最后活跃时间',
    deleted         TINYINT          NOT NULL DEFAULT 0,
    created_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宠物六维属性';
```

### 21. pet_interactions — 互动记录

```sql
CREATE TABLE pet_interactions (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    pet_attribute_id    BIGINT UNSIGNED NOT NULL COMMENT '关联宠物属性 ID (应用层校验存在性)',
    interaction_type    TINYINT         NOT NULL COMMENT '互动类型 (0=喂食, 1=清洁, 2=聊天, 3=玩耍)',
    effect_json         JSON            DEFAULT NULL COMMENT '属性变化效果',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_pet_interactions_type (interaction_type),
    INDEX idx_pet_interactions_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宠物互动记录';
```

### 22. action_logs — 行为日志

> 默认关闭行为模式检测，用户主动启用时才记录。7 天 TTL，定时清理。

```sql
CREATE TABLE action_logs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    module          VARCHAR(64)     NOT NULL COMMENT '模块名',
    action          VARCHAR(128)    NOT NULL COMMENT '行为动作',
    params_summary  VARCHAR(512)    DEFAULT '' COMMENT '参数摘要 (已脱敏)',
    session_id      VARCHAR(128)    DEFAULT '' COMMENT '会话 ID',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_action_logs_module_created (module, created_at),
    INDEX idx_action_logs_created (created_at),
    INDEX idx_action_logs_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行为日志 (7天TTL)';
```

### 23. commands — 命令注册

```sql
CREATE TABLE commands (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '命令名称',
    display_name    VARCHAR(256)    DEFAULT '' COMMENT '显示名称',
    description     VARCHAR(512)    DEFAULT '' COMMENT '命令描述',
    shortcut_key    VARCHAR(32)     DEFAULT '' COMMENT '快捷键',
    module          VARCHAR(64)     NOT NULL COMMENT '所属模块',
    command_type    TINYINT         NOT NULL DEFAULT 0 COMMENT '类型 (0=内置, 1=模块注册)',
    enabled         TINYINT         NOT NULL DEFAULT 1 COMMENT '是否启用',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_commands_name (name),
    INDEX idx_commands_module (module),
    INDEX idx_commands_enabled (deleted, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='命令注册表';
```

### 24. command_usage — 命令使用频率

```sql
CREATE TABLE command_usage (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    command_id      BIGINT UNSIGNED NOT NULL COMMENT '命令 ID (应用层校验存在性)',
    use_count       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '使用次数',
    last_used_at    DATETIME        DEFAULT NULL COMMENT '最后使用时间',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_command_usage_cmd (command_id),
    INDEX idx_command_usage_count (use_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='命令使用频率';
```

### 25. performance_metrics — 性能采样数据

> 保留 360 个采样点，约 30 分钟趋势。Celery Beat 定时清理超过 360 条的旧数据。

```sql
CREATE TABLE performance_metrics (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cpu_percent     DECIMAL(5,2)    NOT NULL DEFAULT 0.00 COMMENT 'CPU 使用率',
    memory_percent  DECIMAL(5,2)    NOT NULL DEFAULT 0.00 COMMENT '内存使用率',
    memory_used_mb  INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '已用内存 (MB)',
    disk_percent    DECIMAL(5,2)    NOT NULL DEFAULT 0.00 COMMENT '磁盘使用率',
    disk_used_gb    INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '已用磁盘 (GB)',
    gpu_percent     DECIMAL(5,2)    DEFAULT NULL COMMENT 'GPU 使用率 (如有)',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_perf_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='性能采样数据 (360点/30分钟)';
```

**清理策略**: Celery Beat 每 5 分钟执行一次清理，保留最新 360 条，删除多余的旧记录：
```sql
-- 先查出保留范围的最小时间，再批量删除更早的记录（避免子查询 IN 效率问题）
DELETE FROM performance_metrics 
WHERE created_at < (
    SELECT min_created FROM (
        SELECT MIN(created_at) AS min_created 
        FROM (
            SELECT created_at FROM performance_metrics 
            ORDER BY created_at DESC LIMIT 360
        ) AS latest
    ) AS tmp
);
```

### 26. soul_configs — 助手人格配置

```sql
CREATE TABLE soul_configs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '助手名称',
    avatar_url      VARCHAR(512)    DEFAULT '' COMMENT '头像地址',
    personality     JSON            NOT NULL COMMENT '性格标签 (配置数据，低频读取)',
    speaking_style  VARCHAR(256)    DEFAULT '' COMMENT '说话风格',
    emotional_tendency TINYINT UNSIGNED NOT NULL DEFAULT 50 COMMENT '情感倾向 (0-100)',
    background      TEXT            DEFAULT NULL COMMENT '背景故事 (应用层软上限 5KB)',
    system_prompt   TEXT            NOT NULL COMMENT '系统提示词 (应用层软上限 10KB)',
    is_active       TINYINT         NOT NULL DEFAULT 1 COMMENT '是否激活',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_soul_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='助手人格配置';
```

### 27. backup_records — 备份记录

```sql
CREATE TABLE backup_records (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    backup_type     TINYINT         NOT NULL COMMENT '备份类型 (0=MySQL, 1=Redis, 2=全量)',
    file_path       VARCHAR(512)    NOT NULL COMMENT '备份文件路径',
    file_size       BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '文件大小 (字节)',
    status          TINYINT         NOT NULL DEFAULT 0 COMMENT '状态 (0=进行中, 1=成功, 2=失败)',
    error_message   VARCHAR(1024)   DEFAULT '' COMMENT '失败原因',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_backup_type (backup_type),
    INDEX idx_backup_status (status),
    INDEX idx_backup_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='备份记录';
```

### 28. prompts — Prompt 版本管理

> 修改时创建新版本而非覆盖，支持回滚和 A/B 测试。

```sql
CREATE TABLE prompts (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT 'Prompt 名称',
    content         TEXT            NOT NULL COMMENT 'Prompt 内容 (应用层软上限 50KB)',
    version         INT UNSIGNED    NOT NULL DEFAULT 1 COMMENT '版本号',
    is_active       TINYINT         NOT NULL DEFAULT 0 COMMENT '是否激活',
    description     VARCHAR(512)    DEFAULT '' COMMENT '版本说明',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_prompts_name (name, version),
    INDEX idx_prompts_active (name, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Prompt 版本管理';
```

### 29. ai_feedback — AI 回答反馈

```sql
CREATE TABLE ai_feedback (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED DEFAULT NULL COMMENT '所属会话 ID (应用层校验存在性)',
    question        TEXT            NOT NULL COMMENT '用户问题 (应用层软上限 10KB)',
    answer          TEXT            NOT NULL COMMENT 'AI 回答 (应用层软上限 50KB)',
    feedback_type   TINYINT         NOT NULL COMMENT '反馈类型 (0=👍, 1=👎)',
    reason_tags     JSON            DEFAULT NULL COMMENT '👎 原因标签',
    reason_text     VARCHAR(2048)   DEFAULT '' COMMENT '👎 自由文本',
    trace_id        VARCHAR(128)    DEFAULT '' COMMENT '请求链路 ID',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_feedback_type (feedback_type),
    INDEX idx_feedback_conversation (conversation_id),
    INDEX idx_feedback_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 回答反馈';
```

### 30. notifications — 通知历史

> WebSocket 推送的通知持久化存储，支持刷新页面后恢复通知历史。

```sql
CREATE TABLE notifications (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id        VARCHAR(128)    DEFAULT '' COMMENT '事件去重 ID (前端 LRU 缓存也用此字段)',
    type            VARCHAR(32)     NOT NULL COMMENT '通知类型 (schedule/workflow/subagent/skill_suggest/system_alert)',
    title           VARCHAR(256)    NOT NULL COMMENT '通知标题',
    message         TEXT            NOT NULL COMMENT '通知内容',
    is_read         TINYINT         NOT NULL DEFAULT 0 COMMENT '是否已读 (0=未读, 1=已读)',
    action_url      VARCHAR(512)    DEFAULT '' COMMENT '点击跳转地址',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_notifications_type_read (type, is_read),
    INDEX idx_notifications_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知历史';
```

### 31. ocr_history — OCR 识别历史

> 截图、文件、粘贴等来源的 OCR 识别记录。

```sql
CREATE TABLE ocr_history (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    image_name      VARCHAR(256)    NOT NULL COMMENT '图片名称',
    image_path      VARCHAR(512)    DEFAULT '' COMMENT '图片存储路径',
    ocr_text        TEXT            NOT NULL COMMENT '识别文本 (应用层软上限 100KB)',
    confidence      DECIMAL(5,4)    NOT NULL DEFAULT 0.0000 COMMENT '识别置信度',
    language        VARCHAR(32)     DEFAULT 'chi_sim+eng' COMMENT '识别语言',
    source_type     TINYINT         NOT NULL DEFAULT 0 COMMENT '来源 (0=截图, 1=文件, 2=粘贴)',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ocr_created (created_at),
    INDEX idx_ocr_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OCR 识别历史';
```

### 32. subagent_runs — 子代理运行记录

> 记录子代理任务的执行状态、步骤和输出。

```sql
CREATE TABLE subagent_runs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_name       VARCHAR(256)    NOT NULL COMMENT '任务名称',
    status          TINYINT         NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=已完成, 3=失败, 4=已终止)',
    priority        TINYINT         NOT NULL DEFAULT 1 COMMENT '优先级 (0=低, 1=正常, 2=高)',
    model           VARCHAR(128)    DEFAULT '' COMMENT '使用的模型',
    current_step    VARCHAR(256)    DEFAULT '' COMMENT '当前执行步骤',
    steps_json      JSON            DEFAULT NULL COMMENT '执行步骤详情',
    input_json      JSON            DEFAULT NULL COMMENT '输入参数',
    output_json     JSON            DEFAULT NULL COMMENT '输出结果',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    started_at      DATETIME        DEFAULT NULL COMMENT '开始时间',
    finished_at     DATETIME        DEFAULT NULL COMMENT '结束时间',
    duration_ms     INT UNSIGNED    DEFAULT 0 COMMENT '执行耗时 (毫秒)',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_subagent_status (status),
    INDEX idx_subagent_created (created_at),
    INDEX idx_subagent_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='子代理运行记录';
```

### 33. pet_models — 宠物模型管理

> 管理 PMX 模型文件、缩略图和动画配置。

```sql
CREATE TABLE pet_models (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '模型名称',
    file_path       VARCHAR(512)    NOT NULL COMMENT '模型文件路径 (.pmx)',
    file_size       BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '文件大小 (字节)',
    thumbnail_path  VARCHAR(512)    DEFAULT '' COMMENT '缩略图路径',
    animation_config JSON           DEFAULT NULL COMMENT '动画配置 (VMD 动作映射)',
    is_default      TINYINT         NOT NULL DEFAULT 0 COMMENT '是否默认模型 (0=否, 1=是)',
    sort_order      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '排序序号',
    enabled         TINYINT         NOT NULL DEFAULT 1 COMMENT '是否启用',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_pet_models_path (file_path),
    INDEX idx_pet_models_default (is_default),
    INDEX idx_pet_models_enabled (deleted, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宠物模型管理';
```

### 34. translate_history — 翻译历史

> 记录翻译请求，支持术语命中追踪和收藏。

```sql
CREATE TABLE translate_history (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_text     TEXT            NOT NULL COMMENT '原文 (应用层软上限 50KB)',
    target_text     TEXT            NOT NULL COMMENT '译文 (应用层软上限 50KB)',
    source_lang     VARCHAR(16)     NOT NULL COMMENT '源语言代码 (zh/en/ja/ko 等)',
    target_lang     VARCHAR(16)     NOT NULL COMMENT '目标语言代码',
    translate_mode  TINYINT         NOT NULL DEFAULT 0 COMMENT '翻译模式 (0=通用, 1=术语)',
    term_hits       JSON            DEFAULT NULL COMMENT '术语命中列表',
    favorite        TINYINT         NOT NULL DEFAULT 0 COMMENT '是否收藏 (0=否, 1=是)',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_translate_history_lang_created (source_lang, target_lang, created_at),
    INDEX idx_translate_history_created (created_at),
    INDEX idx_translate_history_favorite (favorite)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='翻译历史';
```

---

## 🔗 表关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MySQL 表关系总览                               │
│                                                                         │
│  ┌──────────────┐       ┌──────────────┐       ┌────────────────────┐  │
│  │ conversations │◄──────│   messages    │       │    memory_entries   │  │
│  │              │  1:N  │              │       │                    │  │
│  │  id          │───────│ conversation │       │  conversation_id ──│──│──→ conversations
│  │  title       │       │ _id          │       │  summary           │  │
│  │  model_name  │       │  role        │       │  content           │  │
│  │  message_    │       │  content     │       │  qdrant_point_id ──│──│──→ Qdrant memory_vectors
│  │  count       │       │  tool_calls  │       └────────────────────┘  │
│  └──────────────┘       └──────────────┘                               │
│                                                                         │
│  ┌──────────────┐       ┌──────────────┐       ┌────────────────────┐  │
│  │   intents     │◄──────│ intent_usage │       │  knowledge_         │  │
│  │              │  1:N  │              │       │  documents          │  │
│  │  id          │───────│  intent_id   │       │                    │  │
│  │  name        │       │  hit_count   │       │  id                │  │
│  │  target_     │       │  avg_        │       │  filename          │  │
│  │  module      │       │  confidence  │       │  file_type         │  │
│  │  qdrant_     │       └──────────────┘       │  chunk_count       │  │
│  │  point_id ───│──→ Qdrant intent_vectors    └────────┬───────────┘  │
│  └──────────────┘                                       │ 1:N          │
│                                                ┌────────▼───────────┐  │
│  ┌──────────────┐       ┌──────────────┐       │  knowledge_chunks  │  │
│  │    skills     │◄──────│ skill_stats  │       │                    │  │
│  │              │  1:N  │              │       │  document_id ──────│──│──→ knowledge_documents
│  │  id          │───────│  skill_id    │       │  chunk_index       │  │
│  │  name        │       │  call_count  │       │  qdrant_point_id ──│──│──→ Qdrant knowledge_chunks
│  │  enabled     │       │  success_    │       └────────────────────┘  │
│  └──────────────┘       │  count       │                               │
│                         │  avg_        │       ┌────────────────────┐  │
│  ┌──────────────┐       │  duration_ms │       │     schedules       │  │
│  │   workflows   │       └──────────────┘       │                    │  │
│  │              │                               │  id                │  │
│  │  id          │  1:N  ┌──────────────┐       │  title             │  │
│  │  name        │───────│ workflow_    │       │  start_time        │  │
│  │  dag_json    │       │ runs         │       │  reminder_minutes  │  │
│  │  trigger_    │       │              │       │  reminded          │  │
│  │  type        │       │  workflow_id │       └────────────────────┘  │
│  └──────────────┘       │  status      │                               │
│                         │  started_at  │       ┌────────────────────┐  │
│                         │  finished_at │       │  clipboard_items    │  │
│                         └──────┬───────┘       │                    │  │
│                                │ 1:N           │  id                │  │
│                         ┌──────▼───────┐       │  content           │  │
│                         │ workflow_    │       │  content_type      │  │
│                         │ step_runs    │       │  pinned            │  │
│                         │              │       └────────────────────┘  │
│                         │  run_id ─────│──→                            │
│                         │  step_name   │       ┌────────────────────┐  │
│                         │  step_type   │       │     snippets        │  │
│                         │  status      │       │                    │  │
│                         └──────────────┘       │  id                │  │
│                                                │  title             │  │
│  ┌──────────────┐       ┌──────────────┐       │  language          │  │
│  │    tools      │◄──────│ tool_stats   │       │  use_count         │  │
│  │              │  1:N  │              │       └────────────────────┘  │
│  │  id          │───────│  tool_id     │                               │
│  │  name        │       │  call_count  │       ┌────────────────────┐  │
│  │  json_schema │       │  avg_        │       │  pet_attributes     │  │
│  └──────────────┘       │  duration_ms │       │                    │  │
│                         └──────────────┘       │  id                │  │
│                                                │  hunger/clean/mood │  │
│  ┌──────────────┐       ┌──────────────┐       │  health/intimacy/  │  │
│  │   commands    │◄──────│ command_usage│       │  level/exp         │  │
│  │              │  1:N  │              │       │  last_active_at    │  │
│  │  id          │───────│  command_id  │       └────────────────────┘  │
│  │  name        │       │  use_count   │                               │
│  │  shortcut_   │       │  last_used   │       ┌────────────────────┐  │
│  │  key         │       └──────────────┘       │  pet_interactions   │  │
│  └──────────────┘                               │                    │  │
│                                                │  id                │  │
│  ┌──────────────┐       ┌──────────────┐       │  interaction_type  │  │
│  │   settings    │       │ action_logs  │       │  effect_json       │  │
│  │              │       │              │       └────────────────────┘  │
│  │  key (UK)    │       │  module      │                               │
│  │  value       │       │  action      │       ┌────────────────────┐  │
│  │  restart_    │       │  params_     │       │  ai_feedback        │  │
│  │  required    │       │  summary     │       │                    │  │
│  └──────────────┘       └──────────────┘       │  conversation_id ──│──→ conversations
│                                                │  feedback_type     │  │
│  ┌──────────────┐       ┌──────────────┐       │  trace_id          │  │
│  │ soul_configs  │       │performance_  │       └────────────────────┘  │
│  │              │       │ metrics      │                               │
│  │  name        │       │              │       ┌────────────────────┐  │
│  │  personality │       │  cpu_percent │       │  prompts            │  │
│  │  emotional_  │       │  memory_     │       │                    │  │
│  │  tendency    │       │  percent     │       │  name              │  │
│  │  system_     │       │  disk_       │       │  version           │  │
│  │  prompt      │       │  percent     │       │  is_active         │  │
│  │  is_active   │       └──────────────┘       └────────────────────┘  │
│  └──────────────┘                                                       │
│                                                ┌────────────────────┐  │
│  ┌──────────────┐       ┌──────────────┐       │  notifications      │  │
│  │backup_records │       │ ocr_history  │       │                    │  │
│  │              │       │              │       │  event_id          │  │
│  │  backup_type │       │  image_name  │       │  type              │  │
│  │  file_path   │       │  ocr_text    │       │  is_read           │  │
│  │  status      │       │  confidence  │       └────────────────────┘  │
│  └──────────────┘       │  source_type │                               │
│                         └──────────────┘       ┌────────────────────┐  │
│                                                │  subagent_runs      │  │
│  ┌──────────────┐       ┌──────────────┐       │                    │  │
│  │ pet_models    │       │  translate_  │       │  task_name         │  │
│  │              │       │  history     │       │  status            │  │
│  │  name        │       │              │       │  priority          │  │
│  │  file_path   │       │  source_text │       │  model             │  │
│  │  is_default  │       │  target_text │       │  steps_json        │  │
│  │  sort_order  │       │  source_lang │       └────────────────────┘  │
│  │  enabled     │       │  target_lang │                               │
│  └──────────────┘       │  favorite    │                               │
│                         └──────────────┘                               │
│                                                                         │
│  ⚠️ 隐含关联 (表中无外键字段，应用层维护):                                │
│    pet_interactions.pet_attribute_id → 同步更新 pet_attributes 对应属性    │
│    workflows.dag_json 中的节点 → 引用 tools.name 或 skills.name          │
│    snippet_tags → snippets 软删除时级联清理                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 24. expert_teams — 专家团

> 多专家协作工作流，基于 LangGraph Orchestrator-Worker 模式。

```sql
CREATE TABLE expert_team (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  team_name VARCHAR(256) NOT NULL COMMENT '专家团名称',
  description VARCHAR(1024) DEFAULT '' COMMENT '专家团描述',
  icon VARCHAR(64) DEFAULT '👥' COMMENT '图标',
  category VARCHAR(64) DEFAULT '通用' COMMENT '分类',
  orchestrator_prompt TEXT COMMENT '编排器系统提示词',
  synthesizer_prompt TEXT COMMENT '汇总器系统提示词',
  max_rounds INT NOT NULL DEFAULT 3 COMMENT '最大讨论轮次',
  is_enabled TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
  version INT NOT NULL DEFAULT 1 COMMENT '版本号',
  config_json JSON COMMENT '扩展配置',
  is_deleted TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
  gmt_create DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  gmt_modified DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  INDEX idx_expert_team_deleted_enabled (is_deleted, is_enabled),
  INDEX idx_expert_team_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专家团';

CREATE TABLE expert_team_member (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  team_id BIGINT UNSIGNED NOT NULL COMMENT '所属专家团 ID',
  member_name VARCHAR(128) NOT NULL COMMENT '专家名称',
  member_role VARCHAR(128) NOT NULL COMMENT '专家角色 (如: 架构师、测试专家)',
  avatar VARCHAR(64) DEFAULT '🤖' COMMENT '头像 emoji',
  system_prompt TEXT NOT NULL COMMENT '专家系统提示词',
  model_name VARCHAR(128) DEFAULT '' COMMENT '使用的模型名称 (为空用默认)',
  temperature INT DEFAULT 70 COMMENT '温度参数 (x100 存储, 70=0.7)',
  max_tokens INT DEFAULT 2048 COMMENT '最大生成 token 数',
  tools_json JSON COMMENT '可用工具列表',
  sort_order INT DEFAULT 0 COMMENT '排序顺序',
  is_enabled TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
  is_deleted TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
  gmt_create DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  gmt_modified DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  INDEX idx_expert_team_member_team (team_id, is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专家团成员';

CREATE TABLE expert_team_run (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  team_id BIGINT UNSIGNED NOT NULL COMMENT '专家团 ID',
  run_status TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态: 0=待执行 1=运行中 2=已完成 3=失败 4=已取消',
  trigger_type TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '触发方式: 0=手动 1=定时 2=事件',
  input_text TEXT COMMENT '用户输入',
  output_text TEXT COMMENT '最终输出',
  discussion_json JSON COMMENT '讨论过程记录 [{round, expertName, expertRole, content, timestamp}]',
  error_message VARCHAR(2048) DEFAULT '' COMMENT '错误信息',
  round_count INT DEFAULT 0 COMMENT '实际讨论轮次',
  token_usage INT DEFAULT 0 COMMENT '总 token 消耗',
  started_at DATETIME DEFAULT NULL COMMENT '开始时间',
  finished_at DATETIME DEFAULT NULL COMMENT '完成时间',
  duration_ms INT DEFAULT 0 COMMENT '执行耗时 (毫秒)',
  is_deleted TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
  gmt_create DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  gmt_modified DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  INDEX idx_expert_team_run_team (team_id, run_status),
  INDEX idx_expert_team_run_status (run_status),
  INDEX idx_expert_team_run_created (gmt_create)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专家团运行记录';

CREATE TABLE expert_role_skill (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  role_id BIGINT UNSIGNED NOT NULL COMMENT '成员 ID (关联 expert_team_member.id)',
  skill_id BIGINT UNSIGNED NOT NULL COMMENT '技能 ID (关联 skills.id)',
  priority TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '调用优先级 (数值越大越优先)',
  config_override JSON COMMENT '角色级别的技能配置覆盖',
  is_enabled TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
  is_deleted TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
  gmt_create DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  gmt_modified DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  UNIQUE KEY uk_role_skill (role_id, skill_id),
  INDEX idx_expert_role_skill_skill (skill_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色技能绑定';

CREATE TABLE expert_role_run (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT UNSIGNED NOT NULL COMMENT '运行记录 ID (关联 expert_team_run.id)',
  role_id BIGINT UNSIGNED NOT NULL COMMENT '成员 ID (关联 expert_team_member.id)',
  role_name VARCHAR(128) NOT NULL COMMENT '成员名称 (冗余，避免 JOIN)',
  run_status TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态: 0=待运行 1=运行中 2=成功 3=失败 4=跳过',
  round_num INT DEFAULT 0 COMMENT '所在讨论轮次',
  input_json JSON COMMENT '角色输入 (子任务 + 上下文)',
  output_json JSON COMMENT '角色输出 (分析结果)',
  skills_used JSON COMMENT '实际调用的技能列表 [{skill_id, name, status, result}]',
  error_message VARCHAR(2048) DEFAULT '' COMMENT '错误信息',
  started_at DATETIME DEFAULT NULL COMMENT '开始时间',
  finished_at DATETIME DEFAULT NULL COMMENT '完成时间',
  duration_ms INT DEFAULT 0 COMMENT '执行耗时 (毫秒)',
  token_usage INT DEFAULT 0 COMMENT 'token 消耗',
  is_deleted TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
  gmt_create DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  gmt_modified DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  INDEX idx_expert_role_run_run (run_id),
  INDEX idx_expert_role_run_role (role_id),
  INDEX idx_expert_role_run_status (run_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色执行记录';

```

**ER 关系图**:
```
expert_teams (1) ──── (N) expert_team_members
                                  │
                                  │ (N)
                                  ▼
                            expert_role_skills (N) ──── (1) skills

expert_team_runs (1) ──── (N) expert_role_runs
expert_team_members (1) ──── (N) expert_role_runs
```

**设计说明**:
- `temperature` 用整数 x100 存储 (70 = 0.7)，避免浮点精度问题
- `discussion_json` 存储完整的讨论过程，含轮次、专家名、角色、内容、时间戳
- `config_json` 预留扩展字段（如共识阈值、超时配置等）
- `expert_role_skills` 通过唯一索引 `uk_role_skill` 防止重复绑定
- `expert_role_skills.config_override` 可覆盖技能全局配置（如特定角色用不同参数）
- `expert_role_runs` 冗余存储 `role_name`，避免每次查运行记录都要 JOIN members 表
- `expert_role_runs.skills_used` 记录每次执行实际调用了哪些技能及结果

---

## 🔍 索引策略总览

| 表 | 索引 | 类型 | 用途 |
|----|------|------|------|
| messages | (conversation_id, created_at) | 联合 | 按会话查消息，时间排序 |
| intents | (deleted, enabled) | 联合 | 查询启用的意图 |
| action_logs | (module, created_at) | 联合 | 按时间+模块查行为日志 |
| knowledge_documents | (deleted, file_type) | 联合 | 按类型查文档 |
| conversations | (created_at) | 单列 | 按时间查会话 |
| workflow_runs | (workflow_id, status) | 联合 | 按工作流查运行状态 |
| command_usage | (command_id) | 单列 | 查命令使用频率 |
| schedules | (reminded, reminder_minutes, start_time) | 联合 | Celery Beat 扫描待提醒日程 |
| prompts | (name, version) | 联合 | 按名称查 Prompt 版本 |
| prompts | (name, is_active) | 联合 | 查当前激活版本 |
| performance_metrics | (created_at) | 单列 | 按时间查性能趋势 + 清理旧数据 |
| skill_stats | (call_count) | 单列 | 技能排行 |
| snippet_tags | (snippet_id, tag) | 唯一 | 按标签搜索代码片段 |
| notifications | (type, is_read) | 联合 | 按类型筛选已读/未读通知 |
| notifications | (created_at) | 单列 | 按时间查通知历史 |
| pet_interactions | (pet_attribute_id) | 单列 | 查宠物互动记录 |
| workflow_step_runs | (run_id, step_name) | 联合 | 按运行记录查节点详情 |
| workflow_runs | (created_at) | 单列 | 按时间查运行历史 |
| knowledge_chunks | (document_id, chunk_index) | 联合 | 按文档查分块 |
| knowledge_chunks | (qdrant_point_id) | 单列 | 向量 ID 反查 |
| ocr_history | (created_at) | 单列 | 按时间查 OCR 记录 |
| subagent_runs | (status) | 单列 | 按状态查子代理任务 |
| subagent_runs | (priority) | 单列 | 按优先级排序 |
| translate_history | (source_lang, target_lang, created_at) | 联合 | 按语言对查翻译历史 |
| translate_history | (favorite) | 单列 | 筛选收藏翻译 |
| expert_team_members | (team_id, deleted) | 联合 | 按专家团查成员 |
| expert_team_runs | (team_id, status) | 联合 | 按专家团查运行状态 |
| expert_team_runs | (status) | 单列 | 按状态查运行记录 |
| expert_team_runs | (created_at) | 单列 | 按时间查运行历史 |
| expert_role_skills | (role_id, skill_id) | 唯一 | 防止重复绑定 + 按角色查技能 |
| expert_role_skills | (skill_id) | 单列 | 按技能查绑定的角色 |
| expert_role_runs | (run_id) | 联合 | 按运行记录查各角色执行 |
| expert_role_runs | (role_id) | 单列 | 按角色查历史执行 |
| expert_role_runs | (status) | 单列 | 按状态查角色执行 |

---

## 📦 数据一致性保障

| 场景 | 策略 |
|------|------|
| 写入 MySQL 后同步 Qdrant | Celery 异步任务，失败重试 3 次（指数退避），仍失败记修复队列 |
| 删除数据 | MySQL 软删除 (deleted=0→1) + Qdrant payload 标记 deleted:true |
| 更新数据 | 先更新 MySQL → 触发重新 embedding → 更新 Qdrant 向量 |
| 物理清理 | 定时任务每月执行一次，需二次确认 |
| 备份策略 | MySQL: Celery Beat 每 3 天 mysqldump，保留 15 天 |
| | Redis: AOF + RDB，丢失后从 MySQL 重建 |
| | Qdrant: 不单独备份，丢失后从 MySQL 重新 embedding |
| 性能采样清理 | Celery Beat 每 5 分钟清理，保留最新 360 条 |
| 通知清理 | Celery Beat 每天凌晨清理 30 天前的已读通知 |
