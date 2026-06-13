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
| `intent_vectors` | intent.trigger_texts → Qwen3-Embedding | `{ intent_id, is_deleted }` | intent |
| `knowledge_chunks` | 文档分块 → Qwen3-Embedding | `{ doc_id, chunk_index, is_deleted }` | knowledge_document + knowledge_chunk |
| `memory_vectors` | memory_entry.summary → Qwen3-Embedding | `{ memory_id, is_deleted }` | memory_entry |

**关联方式**: MySQL 与 Qdrant 通过 ID 关联，查询时先检索 Qdrant 获取向量匹配结果（含 payload 中的业务 ID），再用 ID 去 MySQL 查询完整业务数据。

**外键策略**: 数据库层不建外键约束（`FOREIGN KEY`），由应用层 Repository 保证引用完整性。原因：① InnoDB 外键有性能开销 ② 批量导入/迁移时外键会阻塞 ③ 软删除场景下外键约束不适用。应用层必须确保：写入前校验关联 ID 存在，删除时级联处理关联数据。

---

## 🗂️ 通用字段约定

> 所有业务表必须包含以下字段，遵循 P3C 规范。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PRIMARY KEY AUTO_INCREMENT | 主键 |
| is_deleted | TINYINT UNSIGNED | NOT NULL DEFAULT 0 | 软删除标记 (0=正常, 1=已删除) |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**命名规约** (遵循 P3C):
- 表名: snake_case，单数形式 (schedule, pet_attribute)
- 字段名: snake_case (created_at, reminder_time)
- 布尔字段: `is_xxx` + `TINYINT UNSIGNED` (is_deleted, is_enabled, is_pinned)
- 非负字段: 必须 `UNSIGNED`
- 索引名: idx_表名_字段名 (idx_message_conversation_id)
- 唯一索引: uk_表名_字段名 (uk_setting_key)
- 字符集: UTF-8MB4

**JSON 字段使用原则**:
- [推荐] 高频查询/过滤/聚合的字段应拆独立表，不用 JSON
- [允许] 低频读取、结构灵活、不需要索引的配置类数据可用 JSON
- 当前使用 JSON 的字段评估:
  - `intent.trigger_texts` → 允许（触发词列表，低频更新，不需单独查询）
  - `message.tool_calls` → 允许（工具调用记录，只读，不需索引）
  - `workflow.dag_json` → 允许（DAG 定义整体读写，不拆分查询）
  - `tool.json_schema` → 允许（MCP inputSchema，整体使用，不拆分）
  - `tool.output_schema` → 允许（MCP outputSchema，可选，整体使用）
  - `tool.annotations` → 允许（MCP Tool Annotations，整体使用）
  - `soul_config.personality` → 允许（配置数据，低频读取）
  - `memory_entry.tags` → 允许（标签列表，低频更新，不需单独查询）

**TEXT 字段长度预警**:
- [推荐] TEXT 字段在应用层设置软上限（如 content 最大 100KB）
- [推荐] 超长文本写入时记录日志告警
- [推荐] 前端展示时做截断处理（如列表页只显示前 200 字）

---

## 📊 表结构详细定义

### 1. setting — 全局配置

> 所有业务配置统一存此表，不使用 .env 文件。KV 结构。

```sql
CREATE TABLE setting (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    settings_key    VARCHAR(128)    NOT NULL COMMENT '配置键',
    key_value       TEXT            NOT NULL COMMENT '配置值 (JSON 字符串)',
    description     VARCHAR(512)    DEFAULT '' COMMENT '配置说明',
    restart_required TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否需要重启: 1=是 0=否',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_setting_key (settings_key),
    INDEX idx_setting_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='全局配置表';
```

### 2. conversation — 会话列表

```sql
CREATE TABLE conversation (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(256)    NOT NULL DEFAULT '' COMMENT '会话标题',
    model_name      VARCHAR(128)    DEFAULT '' COMMENT '使用的对话模型',
    message_count   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '消息数量',
    last_message_at DATETIME        DEFAULT NULL COMMENT '最后消息时间',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_conversation_created_at (created_at),
    INDEX idx_conversation_last_message_at (last_message_at),
    INDEX idx_conversation_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会话列表';
```

### 3. message — 消息记录

> 原始对话历史，完整保留，不向量化。

```sql
CREATE TABLE message (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED NOT NULL COMMENT '所属会话 ID',
    role            VARCHAR(32)     NOT NULL COMMENT '角色 (user/assistant/system/tool)',
    content         TEXT            NOT NULL COMMENT '消息内容 (应用层软上限 100KB)',
    tool_calls      JSON            DEFAULT NULL COMMENT '工具调用信息 (assistant 角色)',
    tool_call_id    VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '工具调用响应 ID (tool 角色)',
    token_count     INT UNSIGNED    DEFAULT 0 COMMENT 'Token 消耗量',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_message_conversation_created (conversation_id, created_at),
    INDEX idx_message_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息记录';
```

### 4. memory_entry — 长期记忆

> 从对话中提炼的摘要和关键信息，非原始消息。

```sql
CREATE TABLE memory_entry (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED DEFAULT NULL COMMENT '来源会话 ID (应用层校验存在性)',
    summary         TEXT            NOT NULL COMMENT '记忆摘要',
    content         TEXT            DEFAULT NULL COMMENT '原始对话内容 (可为空)',
    tags            JSON            DEFAULT NULL COMMENT '标签列表',
    importance      TINYINT UNSIGNED NOT NULL DEFAULT 5 COMMENT '重要度 (1-10)',
    qdrant_point_id VARCHAR(128)    DEFAULT NULL COMMENT 'Qdrant 中的向量 ID',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_memory_entry_conversation (conversation_id),
    INDEX idx_memory_entry_importance (importance),
    INDEX idx_memory_entry_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='长期记忆';
```

### 5. knowledge_document — 知识库文档元数据

```sql
CREATE TABLE knowledge_document (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    filename        VARCHAR(512)    NOT NULL COMMENT '文件名',
    file_type       VARCHAR(32)     NOT NULL COMMENT '文件类型 (pdf/docx/md/txt/json/csv/yaml/html/xml/zip)',
    file_size       BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '文件大小 (字节)',
    chunk_count     INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '分块数量',
    status          TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '处理状态 (0=待处理, 1=处理中, 2=完成, 3=失败)',
    error_message   VARCHAR(1024)   DEFAULT '' COMMENT '失败原因',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_knowledge_document_file_type (file_type),
    INDEX idx_knowledge_document_status (status),
    INDEX idx_knowledge_document_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档元数据';
```

### 6. knowledge_chunk — 知识库文档分块索引

> 记录 Qdrant 中的向量 ID 映射。

```sql
CREATE TABLE knowledge_chunk (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    document_id     BIGINT UNSIGNED NOT NULL COMMENT '所属文档 ID (应用层校验存在性)',
    chunk_index     INT UNSIGNED    NOT NULL COMMENT '分块序号',
    content_preview VARCHAR(512)    DEFAULT '' COMMENT '内容预览 (前 200 字)',
    qdrant_point_id VARCHAR(128)    NOT NULL COMMENT 'Qdrant 中的向量 ID',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_knowledge_chunk_document_index (document_id, chunk_index),
    INDEX idx_knowledge_chunk_qdrant_point (qdrant_point_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档分块索引';
```

### 7. intent — 意图配置

> 文本 + 触发词 + 目标模块 + 元数据。

```sql
CREATE TABLE intent (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '意图名称',
    description     VARCHAR(512)    DEFAULT '' COMMENT '意图描述',
    trigger_texts   JSON            NOT NULL COMMENT '触发词列表 (低频更新，不需单独查询)',
    target_module   VARCHAR(128)    NOT NULL COMMENT '目标模块/工具名',
    tool_names      JSON            DEFAULT NULL COMMENT '关联工具列表: null=全量, []=无工具, ["web_search"]=指定工具',
    metadata        JSON            DEFAULT NULL COMMENT '扩展元数据',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    qdrant_point_id VARCHAR(128)    DEFAULT NULL COMMENT 'Qdrant 中的向量 ID',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_intent_is_deleted_enabled (is_deleted, is_enabled),
    INDEX idx_intent_target_module (target_module)
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
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_intent_usage_intent_id (intent_id),
    INDEX idx_intent_usage_hit_count (hit_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='意图命中统计';
```

### 9. skill — 技能注册

```sql
CREATE TABLE skill (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '技能名称',
    display_name    VARCHAR(256)    DEFAULT '' COMMENT '显示名称',
    description     VARCHAR(1024)   DEFAULT '' COMMENT '技能描述',
    version         VARCHAR(32)     DEFAULT '1.0.0' COMMENT '版本号',
    source          VARCHAR(256)    DEFAULT '' COMMENT '来源 (GitHub URL / local)',
    trigger_words   JSON            NOT NULL DEFAULT (JSON_ARRAY()) COMMENT '触发词列表',
    dependencies    JSON            NOT NULL DEFAULT (JSON_ARRAY()) COMMENT '依赖技能列表',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    config          JSON            DEFAULT NULL COMMENT '技能配置',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_skill_name (name),
    INDEX idx_skill_is_deleted_enabled (is_deleted, is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能注册表';
```

### 10. skill_stat — 技能使用统计

> 仅用于日志展示和优化建议，不限流。

```sql
CREATE TABLE skill_stat (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    skill_id        BIGINT UNSIGNED NOT NULL COMMENT '技能 ID (应用层校验存在性)',
    call_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '调用次数',
    success_count   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '成功次数',
    fail_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '失败次数',
    avg_duration_ms INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '平均耗时 (毫秒)',
    last_called_at  DATETIME        DEFAULT NULL COMMENT '最后调用时间',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_skill_stat_skill_id (skill_id),
    INDEX idx_skill_stat_call_count (call_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能使用统计';
```

### 11. workflow — 工作流定义

```sql
CREATE TABLE workflow (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(256)    NOT NULL COMMENT '工作流名称',
    description     VARCHAR(1024)   DEFAULT '' COMMENT '工作流描述',
    dag_json        JSON            NOT NULL COMMENT 'LangGraph DAG 定义 (节点+边，整体读写)',
    trigger_type    TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '触发方式 (0=手动, 1=定时, 2=事件)',
    cron_expr       VARCHAR(64)     DEFAULT '' COMMENT '定时触发 cron 表达式',
    event_trigger   VARCHAR(256)    DEFAULT '' COMMENT '事件触发条件',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    version         INT UNSIGNED    NOT NULL DEFAULT 1 COMMENT '版本号',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_workflow_is_deleted_enabled (is_deleted, is_enabled),
    INDEX idx_workflow_trigger_type (trigger_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流定义';
```

### 12. workflow_run — 工作流运行记录

```sql
CREATE TABLE workflow_run (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    workflow_id     BIGINT UNSIGNED NOT NULL COMMENT '工作流 ID (应用层校验存在性)',
    status          TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=成功, 3=失败, 4=已取消)',
    trigger_type    TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '触发方式 (0=手动, 1=定时, 2=事件)',
    input_json      JSON            DEFAULT NULL COMMENT '输入参数',
    output_json     JSON            DEFAULT NULL COMMENT '输出结果',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    started_at      DATETIME        DEFAULT NULL COMMENT '开始时间',
    finished_at     DATETIME        DEFAULT NULL COMMENT '结束时间',
    duration_ms     INT UNSIGNED    DEFAULT 0 COMMENT '执行耗时 (毫秒)',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_workflow_run_workflow_status (workflow_id, status),
    INDEX idx_workflow_run_status (status),
    INDEX idx_workflow_run_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流运行记录';
```

### 13. workflow_step_run — 节点执行详情

```sql
CREATE TABLE workflow_step_run (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    run_id          BIGINT UNSIGNED NOT NULL COMMENT '运行记录 ID (应用层校验存在性)',
    step_name       VARCHAR(128)    NOT NULL COMMENT '节点名称',
    step_type       VARCHAR(64)     NOT NULL COMMENT '节点类型 (tool/skill/subagent/llm)',
    status          TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=成功, 3=失败, 4=跳过)',
    input_json      JSON            DEFAULT NULL COMMENT '输入数据',
    output_json     JSON            DEFAULT NULL COMMENT '输出数据',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    started_at      DATETIME        DEFAULT NULL COMMENT '开始时间',
    finished_at     DATETIME        DEFAULT NULL COMMENT '结束时间',
    duration_ms     INT UNSIGNED    DEFAULT 0 COMMENT '执行耗时 (毫秒)',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_workflow_step_run_run_name (run_id, step_name),
    INDEX idx_workflow_step_run_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流节点执行详情';
```

### 14. tool — 工具注册表

```sql
CREATE TABLE tool (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '工具名称',
    display_name    VARCHAR(256)    DEFAULT '' COMMENT '显示名称',
    description     VARCHAR(1024)   NOT NULL COMMENT '工具描述',
    module          VARCHAR(128)    NOT NULL COMMENT '所属模块',
    json_schema     JSON            NOT NULL COMMENT '参数 JSON Schema (MCP inputSchema)',
    output_schema   JSON            DEFAULT NULL COMMENT '输出 JSON Schema (MCP outputSchema, 可选)',
    risk_level      VARCHAR(16)     NOT NULL DEFAULT 'low' COMMENT '风险等级: low/medium/high',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    version         VARCHAR(32)     NOT NULL DEFAULT '1.0.0' COMMENT '工具版本号 (FastMCP v3 组件版本管理)',
    timeout_seconds INT UNSIGNED    NOT NULL DEFAULT 60 COMMENT '工具执行超时 (秒, FastMCP v3 timeout)',
    annotations     JSON            DEFAULT NULL COMMENT 'MCP Tool Annotations (readOnlyHint/destructiveHint/idempotentHint/openWorldHint)',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tool_name (name),
    INDEX idx_tool_module (module),
    INDEX idx_tool_is_deleted_enabled (is_deleted, is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工具注册表';
```

### 15. tool_stat — 工具调用统计

> 仅用于日志展示，不限流。

```sql
CREATE TABLE tool_stat (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tool_id         BIGINT UNSIGNED NOT NULL COMMENT '工具 ID (应用层校验存在性)',
    call_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '调用次数',
    success_count   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '成功次数',
    fail_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '失败次数',
    avg_duration_ms INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '平均耗时 (毫秒)',
    last_called_at  DATETIME        DEFAULT NULL COMMENT '最后调用时间',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tool_stat_tool_id (tool_id),
    INDEX idx_tool_stat_call_count (call_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工具调用统计';
```

### 16. schedule — 日程事件

```sql
CREATE TABLE schedule (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(256)    NOT NULL COMMENT '日程标题',
    description     VARCHAR(2048)   DEFAULT '' COMMENT '日程描述',
    start_time      DATETIME        NOT NULL COMMENT '开始时间',
    end_time        DATETIME        DEFAULT NULL COMMENT '结束时间 (全天事件可为空)',
    is_all_day      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否全天事件: 1=是 0=否',
    reminder_minutes INT UNSIGNED   DEFAULT 0 COMMENT '提前提醒时间 (分钟)',
    is_reminded     TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否已提醒: 1=是 0=否',
    repeat_type     TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '重复类型 (0=不重复, 1=每天, 2=每周, 3=每月, 4=每年)',
    color           VARCHAR(16)     DEFAULT '' COMMENT '日历颜色标记',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_schedule_start_time (start_time),
    INDEX idx_schedule_reminder (is_reminded, reminder_minutes, start_time),
    INDEX idx_schedule_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日程事件';
```

### 17. clipboard_item — 剪贴板历史

```sql
CREATE TABLE clipboard_item (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    content         TEXT            NOT NULL COMMENT '剪贴板内容 (应用层软上限 100KB)',
    content_type    TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '内容类型 (0=文本, 1=代码, 2=图片, 3=链接, 4=文件路径)',
    is_pinned       TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否固定: 1=是 0=否',
    source_app      VARCHAR(256)    DEFAULT '' COMMENT '来源应用',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_clipboard_item_is_pinned (is_pinned),
    INDEX idx_clipboard_item_content_type (content_type),
    INDEX idx_clipboard_item_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='剪贴板历史';
```

### 18. snippet — 代码片段

```sql
CREATE TABLE snippet (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(256)    NOT NULL COMMENT '片段标题',
    content         TEXT            NOT NULL COMMENT '代码内容 (应用层软上限 50KB)',
    language        VARCHAR(64)     DEFAULT '' COMMENT '编程语言',
    use_count       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '使用次数',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_snippet_language (language),
    INDEX idx_snippet_use_count (use_count),
    INDEX idx_snippet_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='代码片段';
```

### 19. snippet_tag — 代码片段标签

> 标签独立存储，支持按标签高效搜索和聚合统计。

```sql
CREATE TABLE snippet_tag (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    snippet_id      BIGINT UNSIGNED NOT NULL COMMENT '片段 ID (应用层校验存在性)',
    tag             VARCHAR(64)     NOT NULL COMMENT '标签名称',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_snippet_tag (snippet_id, tag),
    INDEX idx_snippet_tag_tag (tag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='代码片段标签';
```

### 20. pet_attribute — 宠物属性（单例表）

> 全局只有一只宠物，此表始终只有一行数据。应用层启动时自动初始化。

```sql
CREATE TABLE pet_attribute (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    hunger          TINYINT UNSIGNED NOT NULL DEFAULT 100 COMMENT '饥饿值 (0-100)',
    clean           TINYINT UNSIGNED NOT NULL DEFAULT 100 COMMENT '清洁值 (0-100)',
    mood            TINYINT UNSIGNED NOT NULL DEFAULT 100 COMMENT '心情值 (0-100)',
    health          TINYINT UNSIGNED NOT NULL DEFAULT 100 COMMENT '健康值 (0-100)',
    intimacy        INT UNSIGNED     NOT NULL DEFAULT 0 COMMENT '亲密度',
    level           INT UNSIGNED     NOT NULL DEFAULT 1 COMMENT '等级',
    exp             INT UNSIGNED     NOT NULL DEFAULT 0 COMMENT '经验值',
    last_active_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最后活跃时间',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宠物六维属性';
```

### 21. pet_interaction — 互动记录

```sql
CREATE TABLE pet_interaction (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    pet_attribute_id    BIGINT UNSIGNED NOT NULL COMMENT '关联宠物属性 ID (应用层校验存在性)',
    interaction_type    TINYINT UNSIGNED NOT NULL COMMENT '互动类型 (0=喂食, 1=清洁, 2=聊天, 3=玩耍)',
    effect_json         JSON            DEFAULT NULL COMMENT '属性变化效果',
    is_deleted          TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_pet_interaction_type (interaction_type),
    INDEX idx_pet_interaction_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宠物互动记录';
```

### 22. action_log — 行为日志

> 默认关闭行为模式检测，用户主动启用时才记录。7 天 TTL，定时清理。

```sql
CREATE TABLE action_log (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    module          VARCHAR(64)     NOT NULL COMMENT '模块名',
    action          VARCHAR(128)    NOT NULL COMMENT '行为动作',
    params_summary  VARCHAR(512)    DEFAULT '' COMMENT '参数摘要 (已脱敏)',
    session_id      VARCHAR(128)    DEFAULT '' COMMENT '会话 ID',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_action_log_module_created (module, created_at),
    INDEX idx_action_log_created_at (created_at),
    INDEX idx_action_log_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行为日志 (7天TTL)';
```

### 23. command — 命令注册

```sql
CREATE TABLE command (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '命令名称',
    display_name    VARCHAR(256)    DEFAULT '' COMMENT '显示名称',
    description     VARCHAR(512)    DEFAULT '' COMMENT '命令描述',
    shortcut_key    VARCHAR(32)     DEFAULT '' COMMENT '快捷键',
    module          VARCHAR(64)     NOT NULL COMMENT '所属模块',
    command_type    TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '类型 (0=内置, 1=模块注册)',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_command_name (name),
    INDEX idx_command_module (module),
    INDEX idx_command_is_deleted_enabled (is_deleted, is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='命令注册表';
```

### 24. command_usage — 命令使用频率

```sql
CREATE TABLE command_usage (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    command_id      BIGINT UNSIGNED NOT NULL COMMENT '命令 ID (应用层校验存在性)',
    use_count       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '使用次数',
    last_used_at    DATETIME        DEFAULT NULL COMMENT '最后使用时间',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_command_usage_command_id (command_id),
    INDEX idx_command_usage_use_count (use_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='命令使用频率';
```

### 25. performance_metric — 性能采样数据

> 保留 360 个采样点，约 30 分钟趋势。Celery Beat 定时清理超过 360 条的旧数据。

```sql
CREATE TABLE performance_metric (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cpu_percent     DECIMAL(5,2)    NOT NULL DEFAULT 0.00 COMMENT 'CPU 使用率',
    memory_percent  DECIMAL(5,2)    NOT NULL DEFAULT 0.00 COMMENT '内存使用率',
    memory_used_mb  INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '已用内存 (MB)',
    disk_percent    DECIMAL(5,2)    NOT NULL DEFAULT 0.00 COMMENT '磁盘使用率',
    disk_used_gb    INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '已用磁盘 (GB)',
    gpu_percent     DECIMAL(5,2)    DEFAULT NULL COMMENT 'GPU 使用率 (如有)',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_performance_metric_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='性能采样数据 (360点/30分钟)';
```

**清理策略**: Celery Beat 每 5 分钟执行一次清理，保留最新 360 条，删除多余的旧记录：
```sql
-- 先查出保留范围的最小时间，再批量删除更早的记录（避免子查询 IN 效率问题）
DELETE FROM performance_metric 
WHERE created_at < (
    SELECT min_created FROM (
        SELECT MIN(created_at) AS min_created 
        FROM (
            SELECT created_at FROM performance_metric 
            ORDER BY created_at DESC LIMIT 360
        ) AS latest
    ) AS tmp
);
```

### 26. soul_config — 助手人格配置

```sql
CREATE TABLE soul_config (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '助手名称',
    avatar_url      VARCHAR(512)    DEFAULT '' COMMENT '头像地址',
    personality     JSON            NOT NULL COMMENT '性格标签 (配置数据，低频读取)',
    speaking_style  VARCHAR(256)    DEFAULT '' COMMENT '说话风格',
    background      TEXT            DEFAULT NULL COMMENT '背景故事 (应用层软上限 5KB)',
    system_prompt   TEXT            NOT NULL COMMENT '系统提示词 (应用层软上限 10KB)',
    is_active       TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否激活: 1=是 0=否',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_soul_config_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='助手人格配置';
```

### 27. backup_record — 备份记录

```sql
CREATE TABLE backup_record (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    backup_type     TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '备份类型 (0=MySQL, 1=Redis, 2=全量)',
    file_path       VARCHAR(512)    NOT NULL COMMENT '备份文件路径',
    file_size       BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '文件大小 (字节)',
    status          TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态 (0=进行中, 1=成功, 2=失败)',
    error_message   VARCHAR(1024)   DEFAULT '' COMMENT '失败原因',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_backup_record_type (backup_type),
    INDEX idx_backup_record_status (status),
    INDEX idx_backup_record_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='备份记录';
```

### 28. prompt — Prompt 版本管理

> 修改时创建新版本而非覆盖，支持回滚和 A/B 测试。

```sql
CREATE TABLE prompt (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT 'Prompt 名称',
    content         TEXT            NOT NULL COMMENT 'Prompt 内容 (应用层软上限 50KB)',
    version         INT UNSIGNED    NOT NULL DEFAULT 1 COMMENT '版本号',
    is_active       TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否激活: 1=是 0=否',
    description     VARCHAR(512)    DEFAULT '' COMMENT '版本说明',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_prompt_name_version (name, version),
    INDEX idx_prompt_is_active (name, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Prompt 版本管理';
```

### 29. ai_feedback — AI 回答反馈

```sql
CREATE TABLE ai_feedback (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED DEFAULT NULL COMMENT '所属会话 ID (应用层校验存在性)',
    question        TEXT            NOT NULL COMMENT '用户问题 (应用层软上限 10KB)',
    answer          TEXT            NOT NULL COMMENT 'AI 回答 (应用层软上限 50KB)',
    feedback_type   TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '反馈类型 (0=👍, 1=👎)',
    reason_tags     JSON            DEFAULT NULL COMMENT '👎 原因标签',
    reason_text     VARCHAR(2048)   DEFAULT '' COMMENT '👎 自由文本',
    trace_id        VARCHAR(128)    DEFAULT '' COMMENT '请求链路 ID',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ai_feedback_type (feedback_type),
    INDEX idx_ai_feedback_conversation (conversation_id),
    INDEX idx_ai_feedback_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 回答反馈';
```

### 30. notification — 通知历史

> WebSocket 推送的通知持久化存储，支持刷新页面后恢复通知历史。

```sql
CREATE TABLE notification (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id        VARCHAR(128)    DEFAULT '' COMMENT '事件去重 ID (前端 LRU 缓存也用此字段)',
    type            VARCHAR(32)     NOT NULL COMMENT '通知类型 (schedule/workflow/subagent/skill_suggest/system_alert)',
    title           VARCHAR(256)    NOT NULL COMMENT '通知标题',
    message         TEXT            NOT NULL COMMENT '通知内容',
    is_read         TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否已读: 1=是 0=否',
    action_url      VARCHAR(512)    DEFAULT '' COMMENT '点击跳转地址',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_notification_type_is_read (type, is_read),
    INDEX idx_notification_created_at (created_at)
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
    source_type     TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '来源 (0=截图, 1=文件, 2=粘贴)',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ocr_history_created_at (created_at),
    INDEX idx_ocr_history_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OCR 识别历史';
```

### 32. subagent_run — 子代理运行记录

> 记录子代理任务的执行状态、步骤和输出。

```sql
CREATE TABLE subagent_run (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_name       VARCHAR(256)    NOT NULL COMMENT '任务名称',
    status          TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=已完成, 3=失败, 4=已终止)',
    priority        TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '优先级 (0=低, 1=正常, 2=高)',
    model           VARCHAR(128)    DEFAULT '' COMMENT '使用的模型',
    current_step    VARCHAR(256)    DEFAULT '' COMMENT '当前执行步骤',
    steps_json      JSON            DEFAULT NULL COMMENT '执行步骤详情',
    input_json      JSON            DEFAULT NULL COMMENT '输入参数',
    output_json     JSON            DEFAULT NULL COMMENT '输出结果',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    started_at      DATETIME        DEFAULT NULL COMMENT '开始时间',
    finished_at     DATETIME        DEFAULT NULL COMMENT '结束时间',
    duration_ms     INT UNSIGNED    DEFAULT 0 COMMENT '执行耗时 (毫秒)',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_subagent_run_status (status),
    INDEX idx_subagent_run_created_at (created_at),
    INDEX idx_subagent_run_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='子代理运行记录';
```

### 33. pet_model — 宠物模型管理

> 管理 PMX 模型文件、缩略图和动画配置。

```sql
CREATE TABLE pet_model (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '模型名称',
    file_path       VARCHAR(512)    NOT NULL COMMENT '模型文件路径 (.pmx)',
    file_size       BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '文件大小 (字节)',
    thumbnail_path  VARCHAR(512)    DEFAULT '' COMMENT '缩略图路径',
    animation_config JSON           DEFAULT NULL COMMENT '动画配置 (VMD 动作映射)',
    is_default      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否默认模型: 1=是 0=否',
    sort_order      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '排序序号',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_pet_model_path (file_path),
    INDEX idx_pet_model_is_default (is_default),
    INDEX idx_pet_model_is_deleted_enabled (is_deleted, is_enabled)
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
    translate_mode  TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '翻译模式 (0=通用, 1=术语)',
    term_hits       JSON            DEFAULT NULL COMMENT '术语命中列表',
    is_favorite     TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否收藏: 1=是 0=否',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_translate_history_lang (source_lang, target_lang, created_at),
    INDEX idx_translate_history_created_at (created_at),
    INDEX idx_translate_history_is_favorite (is_favorite)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='翻译历史';
```

### 35. t_user_account — 用户账号

> 用户认证与权限管理，密码通过 bcrypt 哈希存储。

```sql
CREATE TABLE t_user_account (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(64)     NOT NULL COMMENT '用户名（登录账号）',
    password_hash   VARCHAR(128)    NOT NULL COMMENT '密码哈希（bcrypt）',
    nickname        VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '昵称',
    avatar_url      VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '头像 URL',
    user_role       SMALLINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '角色: 0=普通用户 1=管理员',
    is_enabled      SMALLINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户账号表';
```

### 36. markdown_memory — Markdown 记忆文件

> 存储可读的 Markdown 记忆，与 Qdrant 向量互补：Markdown 管可读性，向量管语义搜索。
> 支持 daily log（memory/YYYY-MM-DD.md）和长期记忆（MEMORY.md）两种类型。

```sql
CREATE TABLE markdown_memory (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '用户 ID',
    title           VARCHAR(256)    NOT NULL COMMENT '文件标题（如 2026-06-06 或 MEMORY）',
    content         TEXT            NOT NULL COMMENT 'Markdown 内容',
    memory_type     VARCHAR(32)     NOT NULL DEFAULT 'daily' COMMENT '类型: daily=每日日志, longterm=长期记忆, curated=精选记忆',
    word_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '字数统计',
    qdrant_synced   TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否已同步到 Qdrant: 0=否 1=是',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_md_memory_user_type (user_id, memory_type),
    INDEX idx_md_memory_title (title),
    INDEX idx_md_memory_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Markdown 记忆文件';
```

### 37. cost_record — LLM 调用成本追踪

> 记录每次 LLM 调用的 token 用量和费用，支持按用户/会话/模型/日期维度统计。
> 金额字段用 DECIMAL（不用 FLOAT/DOUBLE，避免精度损失）。

```sql
CREATE TABLE cost_record (
    id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id           BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '用户 ID',
    conversation_id   BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '会话 ID',
    provider_id       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '供应商 ID',
    model_name        VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '模型名称',
    prompt_tokens     INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '输入 token 数',
    completion_tokens INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '输出 token 数',
    total_tokens      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '总 token 数',
    cost_usd          DECIMAL(12,6)   NOT NULL DEFAULT 0 COMMENT '费用（美元）',
    cost_cny          DECIMAL(12,6)   NOT NULL DEFAULT 0 COMMENT '费用（人民币）',
    call_type         VARCHAR(32)     NOT NULL DEFAULT 'chat' COMMENT '调用类型: chat/evaluator/compression/rewrite/summary',
    duration_ms       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '耗时（毫秒）',
    is_stream         TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否流式: 0=否 1=是',
    is_deleted        TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cost_user (user_id),
    INDEX idx_cost_conversation (conversation_id),
    INDEX idx_cost_model (model_name),
    INDEX idx_cost_call_type (call_type),
    INDEX idx_cost_is_deleted (is_deleted),
    INDEX idx_cost_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='LLM 调用成本追踪';
```

---

## 🔗 表关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MySQL 表关系总览                               │
│                                                                         │
│  ┌──────────────┐       ┌──────────────┐       ┌────────────────────┐  │
│  │  conversation │◄──────│   message     │       │   memory_entry      │  │
│  │              │  1:N  │              │       │                    │  │
│  │  id          │───────│ conversation │       │  conversation_id ──│──│──→ conversation
│  │  title       │       │ _id          │       │  summary           │  │
│  │  model_name  │       │  role        │       │  content           │  │
│  │  message_    │       │  content     │       │  qdrant_point_id ──│──│──→ Qdrant memory_vectors
│  │  count       │       │  tool_calls  │       └────────────────────┘  │
│  └──────────────┘       └──────────────┘                               │
│                                                                         │
│  ┌──────────────┐       ┌──────────────┐       ┌────────────────────┐  │
│  │    intent      │◄──────│ intent_usage │       │  knowledge_document │  │
│  │              │  1:N  │              │       │                    │  │
│  │  id          │───────│  intent_id   │       │  id                │  │
│  │  name        │       │  hit_count   │       │  filename          │  │
│  │  target_     │       │  avg_        │       │  file_type         │  │
│  │  module      │       │  confidence  │       │  chunk_count       │  │
│  │  qdrant_     │       └──────────────┘       └────────┬───────────┘  │
│  │  point_id ───│──→ Qdrant intent_vectors              │ 1:N          │
│  └──────────────┘                              ┌────────▼───────────┐  │
│                                                │  knowledge_chunk    │  │
│  ┌──────────────┐       ┌──────────────┐       │                    │  │
│  │    skill      │◄──────│ skill_stat   │       │  document_id ──────│──│──→ knowledge_document
│  │              │  1:N  │              │       │  chunk_index       │  │
│  │  id          │───────│  skill_id    │       │  qdrant_point_id ──│──│──→ Qdrant knowledge_chunks
│  │  name        │       │  call_count  │       └────────────────────┘  │
│  │  is_enabled  │       │  success_    │                               │
│  └──────────────┘       │  count       │       ┌────────────────────┐  │
│                         │  avg_        │       │     schedule        │  │
│  ┌──────────────┐       │  duration_ms │       │                    │  │
│  │   workflow     │       └──────────────┘       │  id                │  │
│  │              │                               │  title             │  │
│  │  id          │  1:N  ┌──────────────┐       │  start_time        │  │
│  │  name        │───────│ workflow_run │       │  reminder_minutes  │  │
│  │  dag_json    │       │              │       │  is_reminded       │  │
│  │  trigger_    │       │  workflow_id │       └────────────────────┘  │
│  │  type        │       │  status      │                               │
│  └──────────────┘       │  started_at  │       ┌────────────────────┐  │
│                         │  finished_at │       │  clipboard_item     │  │
│                         └──────┬───────┘       │                    │  │
│                                │ 1:N           │  id                │  │
│                         ┌──────▼───────┐       │  content           │  │
│                         │ workflow_    │       │  content_type      │  │
│                         │ step_run     │       │  is_pinned         │  │
│                         │              │       └────────────────────┘  │
│                         │  run_id ─────│──→                            │
│                         │  step_name   │       ┌────────────────────┐  │
│                         │  step_type   │       │     snippet         │  │
│                         │  status      │       │                    │  │
│                         └──────────────┘       │  id                │  │
│                                                │  title             │  │
│  ┌──────────────┐       ┌──────────────┐       │  language          │  │
│  │    tool       │◄──────│ tool_stat    │       │  use_count         │  │
│  │              │  1:N  │              │       └────────────────────┘  │
│  │  id          │───────│  tool_id     │                               │
│  │  name        │       │  call_count  │       ┌────────────────────┐  │
│  │  json_schema │       │  avg_        │       │  pet_attribute      │  │
│  └──────────────┘       │  duration_ms │       │                    │  │
│                         └──────────────┘       │  id                │  │
│                                                │  hunger/clean/mood │  │
│  ┌──────────────┐       ┌──────────────┐       │  health/intimacy/  │  │
│  │   command     │◄──────│command_usage │       │  level/exp         │  │
│  │              │  1:N  │              │       │  last_active_at    │  │
│  │  id          │───────│  command_id  │       └────────────────────┘  │
│  │  name        │       │  use_count   │                               │
│  │  shortcut_   │       │  last_used   │       ┌────────────────────┐  │
│  │  key         │       └──────────────┘       │  pet_interaction    │  │
│  └──────────────┘                               │                    │  │
│                                                │  id                │  │
│  ┌──────────────┐       ┌──────────────┐       │  interaction_type  │  │
│  │   setting     │       │ action_log   │       │  effect_json       │  │
│  │              │       │              │       └────────────────────┘  │
│  │  key (UK)    │       │  module      │                               │
│  │  value       │       │  action      │       ┌────────────────────┐  │
│  │  restart_    │       │  params_     │       │  ai_feedback        │  │
│  │  required    │       │  summary     │       │                    │  │
│  └──────────────┘       └──────────────┘       │  conversation_id ──│──→ conversation
│                                                │  feedback_type     │  │
│  ┌──────────────┐       ┌──────────────┐       │  trace_id          │  │
│  │ soul_config   │       │ performance_ │       └────────────────────┘  │
│  │              │       │ metric       │                               │
│  │  name        │       │              │       ┌────────────────────┐  │
│  │  personality │       │  cpu_percent │       │  prompt              │  │
│  │  emotional_  │       │  memory_     │       │                    │  │
│  │  tendency    │       │  percent     │       │  name              │  │
│  │  system_     │       │  disk_       │       │  version           │  │
│  │  prompt      │       │  percent     │       │  is_active         │  │
│  │  is_active   │       └──────────────┘       └────────────────────┘  │
│  └──────────────┘                                                       │
│                                                ┌────────────────────┐  │
│  ┌──────────────┐       ┌──────────────┐       │  notification       │  │
│  │backup_record  │       │ ocr_history  │       │                    │  │
│  │              │       │              │       │  event_id          │  │
│  │  backup_type │       │  image_name  │       │  type              │  │
│  │  file_path   │       │  ocr_text    │       │  is_read           │  │
│  │  status      │       │  confidence  │       └────────────────────┘  │
│  └──────────────┘       │  source_type │                               │
│                         └──────────────┘       ┌────────────────────┐  │
│                                                │  subagent_run       │  │
│  ┌──────────────┐       ┌──────────────┐       │                    │  │
│  │ pet_model     │       │  translate_  │       │  task_name         │  │
│  │              │       │  history     │       │  status            │  │
│  │  name        │       │              │       │  priority          │  │
│  │  file_path   │       │  source_text │       │  model             │  │
│  │  is_default  │       │  target_text │       │  steps_json        │  │
│  │  sort_order  │       │  source_lang │       └────────────────────┘  │
│  │  is_enabled  │       │  target_lang │                               │
│  └──────────────┘       │  is_favorite │                               │
│                         └──────────────┘                               │
│                                                                         │
│  ⚠️ 隐含关联 (表中无外键字段，应用层维护):                                │
│    pet_interaction.pet_attribute_id → 同步更新 pet_attribute 对应属性     │
│    workflow.dag_json 中的节点 → 引用 tool.name 或 skill.name            │
│    snippet_tag → snippet 软删除时级联清理                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 38. expert_team — 专家团

> 多专家协作工作流，基于 LangGraph Orchestrator-Worker 模式。

```sql
CREATE TABLE expert_team (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    team_name           VARCHAR(256)    NOT NULL COMMENT '专家团名称',
    description         VARCHAR(1024)   DEFAULT '' COMMENT '专家团描述',
    icon                VARCHAR(64)     DEFAULT '👥' COMMENT '图标',
    category            VARCHAR(64)     DEFAULT '通用' COMMENT '分类',
    orchestrator_prompt TEXT            COMMENT '编排器系统提示词',
    synthesizer_prompt  TEXT            COMMENT '汇总器系统提示词',
    max_rounds          INT             NOT NULL DEFAULT 3 COMMENT '最大讨论轮次',
    is_enabled          TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    version             INT             NOT NULL DEFAULT 1 COMMENT '版本号',
    config_json         JSON            COMMENT '扩展配置',
    is_deleted          TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    INDEX idx_expert_team_is_deleted_enabled (is_deleted, is_enabled),
    INDEX idx_expert_team_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专家团';
```

### 39. expert_team_member — 专家团成员

```sql
CREATE TABLE expert_team_member (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    team_id         BIGINT UNSIGNED NOT NULL COMMENT '所属专家团 ID',
    member_name     VARCHAR(128)    NOT NULL COMMENT '专家名称',
    member_role     VARCHAR(128)    NOT NULL COMMENT '专家角色 (如: 架构师、测试专家)',
    avatar          VARCHAR(64)     DEFAULT '🤖' COMMENT '头像 emoji',
    system_prompt   TEXT            NOT NULL COMMENT '专家系统提示词',
    model_name      VARCHAR(128)    DEFAULT '' COMMENT '使用的模型名称 (为空用默认)',
    provider_id     BIGINT UNSIGNED DEFAULT NULL COMMENT '供应商 ID (关联 llm_provider)',
    temperature     DECIMAL(3,2)    NOT NULL DEFAULT 0.70 COMMENT '温度参数 (0-2)',
    max_tokens      INT             DEFAULT 2048 COMMENT '最大生成 token 数',
    tools_json      JSON            COMMENT '可用工具列表',
    sort_order      INT             DEFAULT 0 COMMENT '排序顺序',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    INDEX idx_expert_team_member_team_deleted (team_id, is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专家团成员';
```

### 40. expert_team_run — 专家团运行记录

```sql
CREATE TABLE expert_team_run (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    team_id         BIGINT UNSIGNED NOT NULL COMMENT '专家团 ID',
    run_status      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态: 0=待执行 1=运行中 2=已完成 3=失败 4=已取消',
    trigger_type    TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '触发方式: 0=手动 1=定时 2=事件',
    input_text      TEXT            COMMENT '用户输入',
    output_text     TEXT            COMMENT '最终输出',
    discussion_json JSON            COMMENT '讨论过程记录 [{round, expertName, expertRole, content, timestamp}]',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    round_count     INT             DEFAULT 0 COMMENT '实际讨论轮次',
    token_usage     INT             DEFAULT 0 COMMENT '总 token 消耗',
    started_at      DATETIME        DEFAULT NULL COMMENT '开始时间',
    finished_at     DATETIME        DEFAULT NULL COMMENT '完成时间',
    duration_ms     INT             DEFAULT 0 COMMENT '执行耗时 (毫秒)',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    INDEX idx_expert_team_run_team_status (team_id, run_status),
    INDEX idx_expert_team_run_status (run_status),
    INDEX idx_expert_team_run_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专家团运行记录';
```

### 41. expert_role_skill — 角色技能绑定

```sql
CREATE TABLE expert_role_skill (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role_id         BIGINT UNSIGNED NOT NULL COMMENT '成员 ID (关联 expert_team_member.id)',
    skill_id        BIGINT UNSIGNED NOT NULL COMMENT '技能 ID (关联 skill.id)',
    priority        TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '调用优先级 (数值越大越优先)',
    config_override JSON            COMMENT '角色级别的技能配置覆盖',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    UNIQUE KEY uk_role_skill (role_id, skill_id),
    INDEX idx_expert_role_skill_skill_id (skill_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色技能绑定';
```

### 42. expert_role_run — 角色执行记录

```sql
CREATE TABLE expert_role_run (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    run_id          BIGINT UNSIGNED NOT NULL COMMENT '运行记录 ID (关联 expert_team_run.id)',
    role_id         BIGINT UNSIGNED NOT NULL COMMENT '成员 ID (关联 expert_team_member.id)',
    role_name       VARCHAR(128)    NOT NULL COMMENT '成员名称 (冗余，避免 JOIN)',
    run_status      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态: 0=待运行 1=运行中 2=成功 3=失败 4=跳过',
    round_num       INT             DEFAULT 0 COMMENT '所在讨论轮次',
    input_json      JSON            COMMENT '角色输入 (子任务 + 上下文)',
    output_json     JSON            COMMENT '角色输出 (分析结果)',
    skills_used     JSON            COMMENT '实际调用的技能列表 [{skill_id, name, status, result}]',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    started_at      DATETIME        DEFAULT NULL COMMENT '开始时间',
    finished_at     DATETIME        DEFAULT NULL COMMENT '完成时间',
    duration_ms     INT             DEFAULT 0 COMMENT '执行耗时 (毫秒)',
    token_usage     INT             DEFAULT 0 COMMENT 'token 消耗',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    INDEX idx_expert_role_run_run_id (run_id),
    INDEX idx_expert_role_run_role_id (role_id),
    INDEX idx_expert_role_run_status (run_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色执行记录';
```

**ER 关系图**:
```
expert_team (1) ──── (N) expert_team_member
                                  │
                                  │ (N)
                                  ▼
                            expert_role_skill (N) ──── (1) skill

expert_team_run (1) ──── (N) expert_role_run
expert_team_member (1) ──── (N) expert_role_run
```

**设计说明**:
- `temperature` 用 DECIMAL(3,2) 存储，直接存小数（如 0.70）
- `discussion_json` 存储完整的讨论过程，含轮次、专家名、角色、内容、时间戳
- `config_json` 预留扩展字段（如共识阈值、超时配置等）
- `expert_role_skills` 通过唯一索引 `uk_role_skill` 防止重复绑定
- `expert_role_skills.config_override` 可覆盖技能全局配置（如特定角色用不同参数）
- `expert_role_runs` 冗余存储 `role_name`，避免每次查运行记录都要 JOIN members 表
- `expert_role_runs.skills_used` 记录每次执行实际调用了哪些技能及结果

### 43. llm_provider — 大模型供应商配置

```sql
CREATE TABLE llm_provider (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT '供应商显示名称',
    provider_type   VARCHAR(64)     NOT NULL COMMENT '供应商类型: openai/claude/deepseek/ollama/qwen/custom',
    base_url        VARCHAR(512)    NOT NULL COMMENT 'API 基础地址',
    api_key         TEXT                                 COMMENT 'API Key (加密存储)',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1  COMMENT '是否启用: 1=启用 0=禁用',
    is_default      TINYINT UNSIGNED NOT NULL DEFAULT 0  COMMENT '是否默认供应商: 1=是 0=否',
    description     VARCHAR(512)    DEFAULT '' COMMENT '备注说明',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0  COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    INDEX idx_llm_provider_is_enabled (is_enabled),
    INDEX idx_llm_provider_type (provider_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='大模型供应商配置表';
```

**设计说明**:
- `api_key` 用 TEXT 类型存储加密后的密钥，前端显示时脱敏处理
- `is_enabled` 控制供应商是否可用，关闭后前端不展示、后端不调用
- `is_default` 标记默认供应商，同一时间只有一个默认
- 供应商仅负责 API 地址和密钥，模型信息独立存储在 `llm_model` 表

### 44. llm_model — 大模型配置（方案 A: 从 llm_provider.models JSON 拆分）

```sql
CREATE TABLE llm_model (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    provider_id     BIGINT UNSIGNED NOT NULL COMMENT '供应商 ID → llm_provider.id',
    model_name      VARCHAR(128)    NOT NULL COMMENT '实际调用名，如 gpt-4o、qwen3.5:7b',
    display_name    VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '前端显示名，如 GPT-4o',
    context_length  INT UNSIGNED    NOT NULL DEFAULT 4096 COMMENT '上下文窗口长度',
    max_tokens      INT UNSIGNED    NOT NULL DEFAULT 4096 COMMENT '默认最大输出 token',
    temperature     DECIMAL(3,2)    NOT NULL DEFAULT 0.70 COMMENT '默认温度 (0-2)',
    capabilities    JSON            NOT NULL DEFAULT (JSON_OBJECT()) COMMENT '能力标签: {vision, tools, streaming}',
    is_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1  COMMENT '是否启用: 1=启用 0=禁用',
    sort_order      INT UNSIGNED    NOT NULL DEFAULT 0   COMMENT '排序权重，越小越靠前',
    remark          VARCHAR(256)    DEFAULT '' COMMENT '备注',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0  COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    INDEX idx_llm_model_provider_id (provider_id),
    INDEX idx_llm_model_model_name (model_name),
    INDEX idx_llm_model_is_enabled (is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='大模型配置表';
```

**capabilities JSON 字段结构**:
```json
{
  "vision": true,
  "tools": true,
  "streaming": true
}
```

**设计说明**:
- 模型独立管理，可单独启停、排序、配置参数（温度/最大 token/上下文长度）
- `model_name` 为实际调用名（传给 LLM API 的 model 参数），`display_name` 为前端显示名
- `temperature` 用 DECIMAL(3,2) 存储，直接存小数（如 0.70），读取时无需换算
- 供应商删除时联动软删除其下所有模型
- 与 `llm_provider` 通过 `provider_id` 关联，不冗余供应商信息

---

## 🔍 索引策略总览

| 表 | 索引 | 类型 | 用途 |
|----|------|------|------|
| message | (conversation_id, created_at) | 联合 | 按会话查消息，时间排序 |
| intent | (is_deleted, is_enabled) | 联合 | 查询启用的意图 |
| action_log | (module, created_at) | 联合 | 按时间+模块查行为日志 |
| knowledge_document | (is_deleted, file_type) | 联合 | 按类型查文档 |
| conversation | (created_at) | 单列 | 按时间查会话 |
| workflow_run | (workflow_id, status) | 联合 | 按工作流查运行状态 |
| command_usage | (command_id) | 单列 | 查命令使用频率 |
| schedule | (is_reminded, reminder_minutes, start_time) | 联合 | Celery Beat 扫描待提醒日程 |
| prompt | (name, version) | 联合 | 按名称查 Prompt 版本 |
| prompt | (name, is_active) | 联合 | 查当前激活版本 |
| performance_metric | (created_at) | 单列 | 按时间查性能趋势 + 清理旧数据 |
| skill_stat | (call_count) | 单列 | 技能排行 |
| snippet_tag | (snippet_id, tag) | 唯一 | 按标签搜索代码片段 |
| notification | (type, is_read) | 联合 | 按类型筛选已读/未读通知 |
| notification | (created_at) | 单列 | 按时间查通知历史 |
| workflow_step_run | (run_id, step_name) | 联合 | 按运行记录查节点详情 |
| workflow_run | (created_at) | 单列 | 按时间查运行历史 |
| knowledge_chunk | (document_id, chunk_index) | 联合 | 按文档查分块 |
| knowledge_chunk | (qdrant_point_id) | 单列 | 向量 ID 反查 |
| ocr_history | (created_at) | 单列 | 按时间查 OCR 记录 |
| subagent_run | (status) | 单列 | 按状态查子代理任务 |
| subagent_run | (priority) | 单列 | 按优先级排序 |
| translate_history | (source_lang, target_lang, created_at) | 联合 | 按语言对查翻译历史 |
| translate_history | (is_favorite) | 单列 | 筛选收藏翻译 |
| expert_team_member | (team_id, is_deleted) | 联合 | 按专家团查成员 |
| expert_team_run | (team_id, run_status) | 联合 | 按专家团查运行状态 |
| expert_team_run | (run_status) | 单列 | 按状态查运行记录 |
| expert_team_run | (created_at) | 单列 | 按时间查运行历史 |
| expert_role_skill | (role_id, skill_id) | 唯一 | 防止重复绑定 + 按角色查技能 |
| expert_role_skill | (skill_id) | 单列 | 按技能查绑定的角色 |
| expert_role_run | (run_id) | 联合 | 按运行记录查各角色执行 |
| expert_role_run | (role_id) | 单列 | 按角色查历史执行 |
| expert_role_run | (status) | 单列 | 按状态查角色执行 |
| llm_provider | (is_enabled) | 单列 | 筛选启用的供应商 |
| llm_provider | (provider_type) | 单列 | 按类型查供应商 |
| llm_model | (provider_id) | 单列 | 按供应商查模型 |
| llm_model | (model_name) | 单列 | 按模型名查配置 |
| llm_model | (is_enabled) | 单列 | 筛选启用的模型 |
| t_user_account | (username) | 唯一 | 登录账号唯一性约束 |
| markdown_memory | (user_id, memory_type) | 联合 | 按用户和类型查记忆文件 |
| markdown_memory | (title) | 单列 | 按标题查记忆文件 |
| cost_record | (user_id) | 单列 | 按用户查成本 |
| cost_record | (conversation_id) | 单列 | 按会话查成本 |
| cost_record | (model_name) | 单列 | 按模型查成本 |
| cost_record | (call_type) | 单列 | 按调用类型查成本 |

---

## 📦 数据一致性保障

| 场景 | 策略 |
|------|------|
| 写入 MySQL 后同步 Qdrant | Celery 异步任务，失败重试 3 次（指数退避），仍失败记修复队列 |
| 删除数据 | MySQL 软删除 (is_deleted=0→1) + Qdrant payload 标记 deleted:true |
| 更新数据 | 先更新 MySQL → 触发重新 embedding → 更新 Qdrant 向量 |
| 物理清理 | 定时任务每月执行一次，需二次确认 |
| 备份策略 | MySQL: Celery Beat 每 3 天 mysqldump，保留 15 天 |
| | Redis: AOF + RDB，丢失后从 MySQL 重建 |
| | Qdrant: 不单独备份，丢失后从 MySQL 重新 embedding |
| 性能采样清理 | Celery Beat 每 5 分钟清理，保留最新 360 条 |
| 通知清理 | Celery Beat 每天凌晨清理 30 天前的已读通知 |
