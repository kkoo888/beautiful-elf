-- ============================================================
-- Tool 表新增 category 字段（工具分组）
-- 版本: v1.0.0
-- 日期: 2026-06-29
-- 说明: 按功能域对工具分组，支持语义工具选择
-- ============================================================

-- 1. 新增 category 字段
ALTER TABLE tool ADD COLUMN category VARCHAR(32) NOT NULL DEFAULT 'general'
  COMMENT '工具分组: search/file/code/git/data/memory/media/comm/agent/doc/general';

-- 2. 添加索引
CREATE INDEX idx_tool_category ON tool (category);
CREATE INDEX idx_tool_is_deleted_category ON tool (is_deleted, category);

-- 3. 初始化数据：按功能域分组
-- 搜索类
UPDATE tool SET category = 'search' WHERE name IN ('web_search', 'web_fetch', 'web_scrape');

-- 文件类
UPDATE tool SET category = 'file' WHERE name IN ('read_file', 'write_file', 'list_files', 'apply_patch');

-- 代码执行类
UPDATE tool SET category = 'code' WHERE name IN ('execute_code', 'code_review');

-- Git 类
UPDATE tool SET category = 'git' WHERE name IN ('git_log', 'git_commit', 'git_diff', 'git_status');

-- 数据类
UPDATE tool SET category = 'data' WHERE name IN ('query_database', 'data_analyze');

-- 记忆类
UPDATE tool SET category = 'memory' WHERE name IN ('memory_search', 'memory_save', 'session_search');

-- 多媒体类
UPDATE tool SET category = 'media' WHERE name IN ('image_analyze', 'audio_transcribe', 'screenshot', 'text_to_speech', 'image_generate');

-- 通信类
UPDATE tool SET category = 'comm' WHERE name IN ('send_message', 'http_request');

-- Agent 类
UPDATE tool SET category = 'agent' WHERE name IN ('spawn_agent', 'skill_search', 'router_control');

-- 文档类
UPDATE tool SET category = 'doc' WHERE name IN ('parse_pdf', 'translate');

-- 其他（默认 general，无需更新）
