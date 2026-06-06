-- ============================================================
-- Beautiful-Elf P3C 规范迁移脚本
-- 生成时间: 2026-06-01
-- 说明: 按照阿里巴巴 P3C 规约修正所有不合规项
-- ⚠️ 执行前请先备份数据库!
-- ============================================================

-- ============================================================
-- 第一部分: 表重命名 (复数 → 单数)
-- ============================================================

RENAME TABLE `settings` TO `setting`;
RENAME TABLE `conversations` TO `conversation`;
RENAME TABLE `messages` TO `message`;
RENAME TABLE `memory_entries` TO `memory_entry`;
RENAME TABLE `knowledge_documents` TO `knowledge_document`;
RENAME TABLE `knowledge_chunks` TO `knowledge_chunk`;
RENAME TABLE `intents` TO `intent`;
-- intent_usage 已是单数，跳过
RENAME TABLE `skills` TO `skill`;
RENAME TABLE `skill_stats` TO `skill_stat`;
RENAME TABLE `workflows` TO `workflow`;
RENAME TABLE `workflow_runs` TO `workflow_run`;
RENAME TABLE `workflow_step_runs` TO `workflow_step_run`;
RENAME TABLE `tools` TO `tool`;
RENAME TABLE `tool_stats` TO `tool_stat`;
RENAME TABLE `schedules` TO `schedule`;
RENAME TABLE `clipboard_items` TO `clipboard_item`;
RENAME TABLE `snippets` TO `snippet`;
RENAME TABLE `snippet_tags` TO `snippet_tag`;
RENAME TABLE `pet_attributes` TO `pet_attribute`;
RENAME TABLE `pet_interactions` TO `pet_interaction`;
RENAME TABLE `action_logs` TO `action_log`;
RENAME TABLE `commands` TO `command`;
-- command_usage 已是单数，跳过
RENAME TABLE `performance_metrics` TO `performance_metric`;
RENAME TABLE `soul_configs` TO `soul_config`;
RENAME TABLE `backup_records` TO `backup_record`;
RENAME TABLE `prompts` TO `prompt`;
-- ai_feedback 已是单数，跳过
RENAME TABLE `notifications` TO `notification`;
-- ocr_history 已是单数，跳过
RENAME TABLE `subagent_runs` TO `subagent_run`;
RENAME TABLE `pet_models` TO `pet_model`;
-- translate_history 已是单数，跳过
-- expert_team 已是单数，跳过
-- expert_team_member 已是单数，跳过
-- expert_team_run 已是单数，跳过
-- expert_role_skill 已是单数，跳过
-- expert_role_run 已是单数，跳过

-- ============================================================
-- 第二部分: 布尔字段重命名 (xxx → is_xxx) + 补充 UNSIGNED
-- ============================================================

-- 2.1 deleted → is_deleted (所有业务表，同时补充 UNSIGNED)
ALTER TABLE `setting` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `conversation` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `message` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `memory_entry` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `knowledge_document` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `knowledge_chunk` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `intent` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `intent_usage` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `skill` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `skill_stat` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `workflow` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `workflow_run` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `workflow_step_run` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `tool` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `tool_stat` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `schedule` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `clipboard_item` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `snippet` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `snippet_tag` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `pet_attribute` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `pet_interaction` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `action_log` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `command` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `command_usage` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `performance_metric` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `soul_config` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `backup_record` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `prompt` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `ai_feedback` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `notification` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `ocr_history` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `subagent_run` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `pet_model` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';
ALTER TABLE `translate_history` CHANGE COLUMN `deleted` `is_deleted` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否';

-- 2.2 enabled → is_enabled (同时补充 UNSIGNED)
ALTER TABLE `intent` CHANGE COLUMN `enabled` `is_enabled` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否';
ALTER TABLE `skill` CHANGE COLUMN `enabled` `is_enabled` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否';
ALTER TABLE `workflow` CHANGE COLUMN `enabled` `is_enabled` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否';
ALTER TABLE `tool` CHANGE COLUMN `enabled` `is_enabled` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否';
ALTER TABLE `command` CHANGE COLUMN `enabled` `is_enabled` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否';
ALTER TABLE `pet_model` CHANGE COLUMN `enabled` `is_enabled` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用: 1=是 0=否';

-- 2.3 其他布尔字段重命名 + UNSIGNED
ALTER TABLE `schedule` CHANGE COLUMN `all_day` `is_all_day` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否全天事件: 1=是 0=否';
ALTER TABLE `schedule` CHANGE COLUMN `reminded` `is_reminded` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否已提醒: 1=是 0=否';
ALTER TABLE `clipboard_item` CHANGE COLUMN `pinned` `is_pinned` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否固定: 1=是 0=否';
ALTER TABLE `translate_history` CHANGE COLUMN `favorite` `is_favorite` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否收藏: 1=是 0=否';

-- 2.4 is_xxx 字段补充 UNSIGNED (本身命名已对，但缺少 UNSIGNED)
ALTER TABLE `notification` CHANGE COLUMN `is_read` `is_read` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否已读: 1=是 0=否';
ALTER TABLE `soul_config` CHANGE COLUMN `is_active` `is_active` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否激活: 1=是 0=否';
ALTER TABLE `prompt` CHANGE COLUMN `is_active` `is_active` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否激活: 1=是 0=否';
ALTER TABLE `pet_model` CHANGE COLUMN `is_default` `is_default` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否默认模型: 1=是 0=否';

-- ============================================================
-- 第三部分: 非负 TINYINT 字段补充 UNSIGNED
-- ============================================================

ALTER TABLE `setting` CHANGE COLUMN `restart_required` `restart_required` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否需要重启: 1=是 0=否';
ALTER TABLE `knowledge_document` CHANGE COLUMN `status` `status` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '处理状态 (0=待处理, 1=处理中, 2=完成, 3=失败)';
ALTER TABLE `workflow` CHANGE COLUMN `trigger_type` `trigger_type` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '触发方式 (0=手动, 1=定时, 2=事件)';
ALTER TABLE `workflow_run` CHANGE COLUMN `status` `status` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=成功, 3=失败, 4=已取消)';
ALTER TABLE `workflow_run` CHANGE COLUMN `trigger_type` `trigger_type` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '触发方式 (0=手动, 1=定时, 2=事件)';
ALTER TABLE `workflow_step_run` CHANGE COLUMN `status` `status` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=成功, 3=失败, 4=跳过)';
ALTER TABLE `schedule` CHANGE COLUMN `repeat_type` `repeat_type` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '重复类型 (0=不重复, 1=每天, 2=每周, 3=每月, 4=每年)';
ALTER TABLE `clipboard_item` CHANGE COLUMN `content_type` `content_type` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '内容类型 (0=文本, 1=代码, 2=图片, 3=链接, 4=文件路径)';
ALTER TABLE `pet_interaction` CHANGE COLUMN `interaction_type` `interaction_type` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '互动类型 (0=喂食, 1=清洁, 2=聊天, 3=玩耍)';
ALTER TABLE `command` CHANGE COLUMN `command_type` `command_type` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '类型 (0=内置, 1=模块注册)';
ALTER TABLE `backup_record` CHANGE COLUMN `backup_type` `backup_type` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '备份类型 (0=MySQL, 1=Redis, 2=全量)';
ALTER TABLE `backup_record` CHANGE COLUMN `status` `status` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态 (0=进行中, 1=成功, 2=失败)';
ALTER TABLE `ai_feedback` CHANGE COLUMN `feedback_type` `feedback_type` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '反馈类型 (0=👍, 1=👎)';
ALTER TABLE `ocr_history` CHANGE COLUMN `source_type` `source_type` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '来源 (0=截图, 1=文件, 2=粘贴)';
ALTER TABLE `subagent_run` CHANGE COLUMN `status` `status` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态 (0=待运行, 1=运行中, 2=已完成, 3=失败, 4=已终止)';
ALTER TABLE `subagent_run` CHANGE COLUMN `priority` `priority` TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '优先级 (0=低, 1=正常, 2=高)';

-- ============================================================
-- 第四部分: expert_team* 表时间字段统一 (gmt_* → created_at/updated_at)
-- ============================================================

ALTER TABLE `expert_team` CHANGE COLUMN `gmt_create` `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';
ALTER TABLE `expert_team` CHANGE COLUMN `gmt_modified` `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间';

ALTER TABLE `expert_team_member` CHANGE COLUMN `gmt_create` `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';
ALTER TABLE `expert_team_member` CHANGE COLUMN `gmt_modified` `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间';

ALTER TABLE `expert_team_run` CHANGE COLUMN `gmt_create` `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';
ALTER TABLE `expert_team_run` CHANGE COLUMN `gmt_modified` `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间';

ALTER TABLE `expert_role_skill` CHANGE COLUMN `gmt_create` `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';
ALTER TABLE `expert_role_skill` CHANGE COLUMN `gmt_modified` `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间';

ALTER TABLE `expert_role_run` CHANGE COLUMN `gmt_create` `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';
ALTER TABLE `expert_role_run` CHANGE COLUMN `gmt_modified` `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间';

-- ============================================================
-- 第五部分: 索引名更新 (跟随字段名和表名变更)
-- ============================================================

-- 5.1 布尔字段相关索引
ALTER TABLE `setting` DROP INDEX `idx_settings_deleted`, ADD INDEX `idx_setting_is_deleted` (`is_deleted`);
ALTER TABLE `conversation` DROP INDEX `idx_conversations_deleted`, ADD INDEX `idx_conversation_is_deleted` (`is_deleted`);
ALTER TABLE `conversation` DROP INDEX `idx_conversations_created`, ADD INDEX `idx_conversation_created_at` (`created_at`);
ALTER TABLE `conversation` DROP INDEX `idx_conversations_last_msg`, ADD INDEX `idx_conversation_last_message_at` (`last_message_at`);
ALTER TABLE `message` DROP INDEX `idx_messages_conversation`, ADD INDEX `idx_message_conversation_created` (`conversation_id`, `created_at`);
ALTER TABLE `message` DROP INDEX `idx_messages_role`, ADD INDEX `idx_message_role` (`role`);
ALTER TABLE `memory_entry` DROP INDEX `idx_memory_conversation`, ADD INDEX `idx_memory_entry_conversation` (`conversation_id`);
ALTER TABLE `memory_entry` DROP INDEX `idx_memory_importance`, ADD INDEX `idx_memory_entry_importance` (`importance`);
ALTER TABLE `memory_entry` DROP INDEX `idx_memory_deleted`, ADD INDEX `idx_memory_entry_is_deleted` (`is_deleted`);
ALTER TABLE `knowledge_document` DROP INDEX `idx_knowledge_type`, ADD INDEX `idx_knowledge_document_file_type` (`file_type`);
ALTER TABLE `knowledge_document` DROP INDEX `idx_knowledge_status`, ADD INDEX `idx_knowledge_document_status` (`status`);
ALTER TABLE `knowledge_document` DROP INDEX `idx_knowledge_deleted`, ADD INDEX `idx_knowledge_document_is_deleted` (`is_deleted`);
ALTER TABLE `knowledge_chunk` DROP INDEX `idx_chunks_document`, ADD INDEX `idx_knowledge_chunk_document_index` (`document_id`, `chunk_index`);
ALTER TABLE `knowledge_chunk` DROP INDEX `idx_chunks_qdrant`, ADD INDEX `idx_knowledge_chunk_qdrant_point` (`qdrant_point_id`);
ALTER TABLE `intent` DROP INDEX `idx_intents_enabled`, ADD INDEX `idx_intent_is_deleted_enabled` (`is_deleted`, `is_enabled`);
ALTER TABLE `intent` DROP INDEX `idx_intents_module`, ADD INDEX `idx_intent_target_module` (`target_module`);
ALTER TABLE `intent_usage` DROP INDEX `idx_usage_intent`, ADD INDEX `idx_intent_usage_intent_id` (`intent_id`);
ALTER TABLE `intent_usage` DROP INDEX `idx_usage_hit_count`, ADD INDEX `idx_intent_usage_hit_count` (`hit_count`);
ALTER TABLE `skill` DROP INDEX `idx_skills_enabled`, ADD INDEX `idx_skill_is_deleted_enabled` (`is_deleted`, `is_enabled`);
ALTER TABLE `skill_stat` DROP INDEX `idx_skill_stats_skill`, ADD INDEX `idx_skill_stat_skill_id` (`skill_id`);
ALTER TABLE `skill_stat` DROP INDEX `idx_skill_stats_calls`, ADD INDEX `idx_skill_stat_call_count` (`call_count`);
ALTER TABLE `workflow` DROP INDEX `idx_workflows_enabled`, ADD INDEX `idx_workflow_is_deleted_enabled` (`is_deleted`, `is_enabled`);
ALTER TABLE `workflow` DROP INDEX `idx_workflows_trigger`, ADD INDEX `idx_workflow_trigger_type` (`trigger_type`);
ALTER TABLE `workflow_run` DROP INDEX `idx_wf_runs_workflow`, ADD INDEX `idx_workflow_run_workflow_status` (`workflow_id`, `status`);
ALTER TABLE `workflow_run` DROP INDEX `idx_wf_runs_status`, ADD INDEX `idx_workflow_run_status` (`status`);
ALTER TABLE `workflow_run` DROP INDEX `idx_wf_runs_created`, ADD INDEX `idx_workflow_run_created_at` (`created_at`);
ALTER TABLE `workflow_step_run` DROP INDEX `idx_step_runs_run`, ADD INDEX `idx_workflow_step_run_run_name` (`run_id`, `step_name`);
ALTER TABLE `workflow_step_run` DROP INDEX `idx_step_runs_status`, ADD INDEX `idx_workflow_step_run_status` (`status`);
ALTER TABLE `tool` DROP INDEX `idx_tools_module`, ADD INDEX `idx_tool_module` (`module`);
ALTER TABLE `tool` DROP INDEX `idx_tools_enabled`, ADD INDEX `idx_tool_is_deleted_enabled` (`is_deleted`, `is_enabled`);
ALTER TABLE `tool_stat` DROP INDEX `idx_tool_stats_tool`, ADD INDEX `idx_tool_stat_tool_id` (`tool_id`);
ALTER TABLE `tool_stat` DROP INDEX `idx_tool_stats_calls`, ADD INDEX `idx_tool_stat_call_count` (`call_count`);
ALTER TABLE `schedule` DROP INDEX `idx_schedules_start`, ADD INDEX `idx_schedule_start_time` (`start_time`);
ALTER TABLE `schedule` DROP INDEX `idx_schedules_reminder`, ADD INDEX `idx_schedule_reminder` (`is_reminded`, `reminder_minutes`, `start_time`);
ALTER TABLE `schedule` DROP INDEX `idx_schedules_deleted`, ADD INDEX `idx_schedule_is_deleted` (`is_deleted`);
ALTER TABLE `clipboard_item` DROP INDEX `idx_clipboard_pinned`, ADD INDEX `idx_clipboard_item_is_pinned` (`is_pinned`);
ALTER TABLE `clipboard_item` DROP INDEX `idx_clipboard_type`, ADD INDEX `idx_clipboard_item_content_type` (`content_type`);
ALTER TABLE `clipboard_item` DROP INDEX `idx_clipboard_created`, ADD INDEX `idx_clipboard_item_created_at` (`created_at`);
ALTER TABLE `snippet` DROP INDEX `idx_snippets_language`, ADD INDEX `idx_snippet_language` (`language`);
ALTER TABLE `snippet` DROP INDEX `idx_snippets_use_count`, ADD INDEX `idx_snippet_use_count` (`use_count`);
ALTER TABLE `snippet` DROP INDEX `idx_snippets_deleted`, ADD INDEX `idx_snippet_is_deleted` (`is_deleted`);
ALTER TABLE `snippet_tag` DROP INDEX `idx_snippet_tags_tag`, ADD INDEX `idx_snippet_tag_tag` (`tag`);
ALTER TABLE `pet_interaction` DROP INDEX `idx_pet_interactions_type`, ADD INDEX `idx_pet_interaction_type` (`interaction_type`);
ALTER TABLE `pet_interaction` DROP INDEX `idx_pet_interactions_created`, ADD INDEX `idx_pet_interaction_created_at` (`created_at`);
ALTER TABLE `action_log` DROP INDEX `idx_action_logs_module_created`, ADD INDEX `idx_action_log_module_created` (`module`, `created_at`);
ALTER TABLE `action_log` DROP INDEX `idx_action_logs_created`, ADD INDEX `idx_action_log_created_at` (`created_at`);
ALTER TABLE `action_log` DROP INDEX `idx_action_logs_action`, ADD INDEX `idx_action_log_action` (`action`);
ALTER TABLE `command` DROP INDEX `idx_commands_module`, ADD INDEX `idx_command_module` (`module`);
ALTER TABLE `command` DROP INDEX `idx_commands_enabled`, ADD INDEX `idx_command_is_deleted_enabled` (`is_deleted`, `is_enabled`);
ALTER TABLE `command_usage` DROP INDEX `idx_command_usage_cmd`, ADD INDEX `idx_command_usage_command_id` (`command_id`);
ALTER TABLE `command_usage` DROP INDEX `idx_command_usage_count`, ADD INDEX `idx_command_usage_use_count` (`use_count`);
ALTER TABLE `performance_metric` DROP INDEX `idx_perf_created`, ADD INDEX `idx_performance_metric_created_at` (`created_at`);
ALTER TABLE `soul_config` DROP INDEX `idx_soul_active`, ADD INDEX `idx_soul_config_is_active` (`is_active`);
ALTER TABLE `backup_record` DROP INDEX `idx_backup_type`, ADD INDEX `idx_backup_record_type` (`backup_type`);
ALTER TABLE `backup_record` DROP INDEX `idx_backup_status`, ADD INDEX `idx_backup_record_status` (`status`);
ALTER TABLE `backup_record` DROP INDEX `idx_backup_created`, ADD INDEX `idx_backup_record_created_at` (`created_at`);
ALTER TABLE `prompt` DROP INDEX `idx_prompts_name`, ADD INDEX `idx_prompt_name_version` (`name`, `version`);
ALTER TABLE `prompt` DROP INDEX `idx_prompts_active`, ADD INDEX `idx_prompt_is_active` (`name`, `is_active`);
ALTER TABLE `ai_feedback` DROP INDEX `idx_feedback_type`, ADD INDEX `idx_ai_feedback_type` (`feedback_type`);
ALTER TABLE `ai_feedback` DROP INDEX `idx_feedback_conversation`, ADD INDEX `idx_ai_feedback_conversation` (`conversation_id`);
ALTER TABLE `ai_feedback` DROP INDEX `idx_feedback_created`, ADD INDEX `idx_ai_feedback_created_at` (`created_at`);
ALTER TABLE `notification` DROP INDEX `idx_notifications_type_read`, ADD INDEX `idx_notification_type_is_read` (`type`, `is_read`);
ALTER TABLE `notification` DROP INDEX `idx_notifications_created`, ADD INDEX `idx_notification_created_at` (`created_at`);
ALTER TABLE `ocr_history` DROP INDEX `idx_ocr_created`, ADD INDEX `idx_ocr_history_created_at` (`created_at`);
ALTER TABLE `ocr_history` DROP INDEX `idx_ocr_deleted`, ADD INDEX `idx_ocr_history_is_deleted` (`is_deleted`);
ALTER TABLE `subagent_run` DROP INDEX `idx_subagent_status`, ADD INDEX `idx_subagent_run_status` (`status`);
ALTER TABLE `subagent_run` DROP INDEX `idx_subagent_created`, ADD INDEX `idx_subagent_run_created_at` (`created_at`);
ALTER TABLE `subagent_run` DROP INDEX `idx_subagent_priority`, ADD INDEX `idx_subagent_run_priority` (`priority`);
ALTER TABLE `pet_model` DROP INDEX `idx_pet_models_default`, ADD INDEX `idx_pet_model_is_default` (`is_default`);
ALTER TABLE `pet_model` DROP INDEX `idx_pet_models_enabled`, ADD INDEX `idx_pet_model_is_deleted_enabled` (`is_deleted`, `is_enabled`);
ALTER TABLE `translate_history` DROP INDEX `idx_translate_history_lang_created`, ADD INDEX `idx_translate_history_lang` (`source_lang`, `target_lang`, `created_at`);
ALTER TABLE `translate_history` DROP INDEX `idx_translate_history_created`, ADD INDEX `idx_translate_history_created_at` (`created_at`);
ALTER TABLE `translate_history` DROP INDEX `idx_translate_history_favorite`, ADD INDEX `idx_translate_history_is_favorite` (`is_favorite`);
ALTER TABLE `expert_team` DROP INDEX `idx_expert_team_deleted_enabled`, ADD INDEX `idx_expert_team_is_deleted_enabled` (`is_deleted`, `is_enabled`);
ALTER TABLE `expert_team_member` DROP INDEX `idx_expert_team_member_team`, ADD INDEX `idx_expert_team_member_team_deleted` (`team_id`, `is_deleted`);
ALTER TABLE `expert_team_run` DROP INDEX `idx_expert_team_run_team`, ADD INDEX `idx_expert_team_run_team_status` (`team_id`, `run_status`);
ALTER TABLE `expert_team_run` DROP INDEX `idx_expert_team_run_created`, ADD INDEX `idx_expert_team_run_created_at` (`created_at`);
ALTER TABLE `expert_role_skill` DROP INDEX `idx_expert_role_skill_skill`, ADD INDEX `idx_expert_role_skill_skill_id` (`skill_id`);
ALTER TABLE `expert_role_run` DROP INDEX `idx_expert_role_run_run`, ADD INDEX `idx_expert_role_run_run_id` (`run_id`);
ALTER TABLE `expert_role_run` DROP INDEX `idx_expert_role_run_role`, ADD INDEX `idx_expert_role_run_role_id` (`role_id`);

-- ============================================================
-- 第四部分: 新增表 (2026-06-02)
-- ============================================================

-- 大模型供应商配置表
CREATE TABLE IF NOT EXISTS `llm_provider` (
  `id`            BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name`          VARCHAR(128)     NOT NULL                COMMENT '供应商显示名称',
  `provider_type` VARCHAR(64)      NOT NULL                COMMENT '供应商类型: openai/claude/deepseek/ollama/qwen/custom',
  `base_url`      VARCHAR(512)     NOT NULL                COMMENT 'API 基础地址',
  `api_key`       TEXT                                     COMMENT 'API Key (加密存储)',
  `models`        JSON             NOT NULL DEFAULT (JSON_ARRAY()) COMMENT '可用模型列表 JSON',
  `is_enabled`    TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '是否启用: 1=启用 0=禁用',
  `is_default`    TINYINT UNSIGNED NOT NULL DEFAULT 0      COMMENT '是否默认供应商: 1=是 0=否',
  `description`   VARCHAR(512)     DEFAULT ''               COMMENT '备注说明',
  `is_deleted`    TINYINT UNSIGNED NOT NULL DEFAULT 0      COMMENT '是否删除: 1=是 0=否',
  `created_at`    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_llm_provider_is_enabled` (`is_enabled`),
  INDEX `idx_llm_provider_type` (`provider_type`),
  INDEX `idx_llm_provider_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='大模型供应商配置表';

-- ============================================================
-- 完成! 请验证所有变更是否正确
-- ============================================================
