/*
 工具表增量迁移 — v1.0.1
 
 修复 + 新增工具，适用于已执行过 tool.sql 的环境。
 执行方式: mysql -u root -p beautiful_elf < tool_migration_v1.0.1.sql
 
 日期: 2026-06-27
*/

SET NAMES utf8mb4;

-- ============================================
-- 1. 修复已有工具的 annotations / schema
-- ============================================

-- write_file: idempotentHint true -> false（覆盖写不是幂等的）
UPDATE `tool` SET
  `annotations` = JSON_SET(`annotations`, '$.idempotentHint', false),
  `updated_at` = NOW()
WHERE `name` = 'write_file';

-- exec_command: openWorldHint + sandboxHint + timeout 10 -> 30
UPDATE `tool` SET
  `annotations` = JSON_SET(`annotations`, '$.openWorldHint', true, '$.sandboxHint', true),
  `json_schema` = JSON_SET(`json_schema`, '$.properties.timeout.default', 30),
  `updated_at` = NOW()
WHERE `name` = 'exec_command';

-- spawn_agent: openWorldHint false -> true（子 Agent 可执行外部操作）
UPDATE `tool` SET
  `annotations` = JSON_SET(`annotations`, '$.openWorldHint', true),
  `updated_at` = NOW()
WHERE `name` = 'spawn_agent';

-- web_search: output_schema error type object -> string
UPDATE `tool` SET
  `output_schema` = JSON_SET(`output_schema`, '$.properties.error.type', 'string'),
  `updated_at` = NOW()
WHERE `name` = 'web_search';

-- execute_code: 加 sandboxHint
UPDATE `tool` SET
  `annotations` = JSON_SET(`annotations`, '$.sandboxHint', true),
  `updated_at` = NOW()
WHERE `name` = 'execute_code';

-- ============================================
-- 2. 新增工具（已存在则跳过）
-- ============================================

INSERT IGNORE INTO `tool` (`name`, `display_name`, `description`, `module`, `json_schema`, `output_schema`, `risk_level`, `is_enabled`, `timeout_seconds`, `strict_mode`, `annotations`) VALUES

-- HTTP 请求（调用外部 API）
('http_request', 'HTTP 请求', '发送 HTTP 请求调用外部 API（GET/POST/PUT/DELETE），支持自定义 Headers 和 Body', 'web',
 '{"type": "object", "required": ["method", "url"], "properties": {"method": {"enum": ["GET", "POST", "PUT", "DELETE", "PATCH"], "type": "string", "description": "HTTP 方法"}, "url": {"type": "string", "description": "请求 URL"}, "headers": {"type": "object", "description": "请求头"}, "body": {"type": "object", "description": "请求体（JSON）"}, "timeout": {"type": "integer", "default": 30, "description": "超时秒数"}}}',
 '{"type": "object", "properties": {"error": {"type": "string"}, "status_code": {"type": "integer"}, "headers": {"type": "object"}, "body": {"type": "string"}}}',
 'medium', 1, 30, 0,
 '{"readOnlyHint": false, "openWorldHint": true, "idempotentHint": false, "destructiveHint": false, "version": "1.0.0"}'),

-- 图片分析（OCR / 描述 / 图表解读）
('image_analyze', '图片分析', '分析图片内容：OCR 文字提取、物体识别、场景描述、图表解读（支持 URL 和本地路径）', 'media',
 '{"type": "object", "required": ["image"], "properties": {"image": {"type": "string", "description": "图片 URL 或本地路径"}, "prompt": {"type": "string", "default": "描述这张图片", "description": "分析指令"}}}',
 '{"type": "object", "properties": {"error": {"type": "string"}, "description": {"type": "string"}, "text": {"type": "string"}}}',
 'low', 1, 60, 0,
 '{"readOnlyHint": true, "openWorldHint": true, "idempotentHint": true, "destructiveHint": false, "version": "1.0.0"}'),

-- 网页结构化提取
('web_scrape', '网页结构化提取', '从网页中用 CSS 选择器或 XPath 提取结构化数据（表格、列表、特定元素）', 'web',
 '{"type": "object", "required": ["url", "selector"], "properties": {"url": {"type": "string", "description": "目标 URL"}, "selector": {"type": "string", "description": "CSS 选择器或 XPath"}, "extract": {"enum": ["text", "html", "attr"], "type": "string", "default": "text", "description": "提取类型"}, "multiple": {"type": "boolean", "default": false, "description": "是否提取所有匹配项"}}}',
 '{"type": "object", "properties": {"error": {"type": "string"}, "results": {"type": "array", "items": {"type": "string"}}, "count": {"type": "integer"}}}',
 'low', 1, 30, 0,
 '{"readOnlyHint": true, "openWorldHint": true, "idempotentHint": true, "destructiveHint": false, "version": "1.0.0"}'),

-- 多语言翻译
('translate', '翻译', '多语言翻译（支持中英日韩法德西等 50+ 语言，自动检测源语言）', 'text',
 '{"type": "object", "required": ["text", "target_lang"], "properties": {"text": {"type": "string", "description": "要翻译的文本"}, "target_lang": {"type": "string", "description": "目标语言代码（如 zh/en/ja/ko）"}, "source_lang": {"type": "string", "description": "源语言代码（可选，自动检测）"}}}',
 '{"type": "object", "properties": {"error": {"type": "string"}, "translated": {"type": "string"}, "source_lang": {"type": "string"}, "target_lang": {"type": "string"}}}',
 'low', 1, 15, 0,
 '{"readOnlyHint": true, "openWorldHint": false, "idempotentHint": true, "destructiveHint": false, "version": "1.0.0"}'),

-- 网页截图
('screenshot', '网页截图', '对指定 URL 进行网页截图（支持全页/可视区域，返回 PNG 图片路径）', 'web',
 '{"type": "object", "required": ["url"], "properties": {"url": {"type": "string", "description": "目标 URL"}, "full_page": {"type": "boolean", "default": false, "description": "是否截取全页"}, "width": {"type": "integer", "default": 1280, "description": "视口宽度"}}}',
 '{"type": "object", "properties": {"error": {"type": "string"}, "path": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}}}',
 'low', 1, 30, 0,
 '{"readOnlyHint": true, "openWorldHint": true, "idempotentHint": true, "destructiveHint": false, "version": "1.0.0"}'),

-- 语音转文字
('audio_transcribe', '语音转文字', '将音频文件转录为文字（支持中英文，支持 WAV/MP3/FLAC 格式）', 'media',
 '{"type": "object", "required": ["audio"], "properties": {"audio": {"type": "string", "description": "音频文件路径或 URL"}, "language": {"type": "string", "default": "zh", "description": "语言代码"}}}',
 '{"type": "object", "properties": {"error": {"type": "string"}, "text": {"type": "string"}, "duration": {"type": "number"}}}',
 'low', 1, 120, 0,
 '{"readOnlyHint": true, "openWorldHint": false, "idempotentHint": true, "destructiveHint": false, "version": "1.0.0"}'),

-- 数据分析
('data_analyze', '数据分析', '对 CSV/JSON 数据进行统计分析（均值/中位数/分布/相关性等）', 'data',
 '{"type": "object", "required": ["data"], "properties": {"data": {"type": "string", "description": "数据路径（CSV/JSON）或内联数据"}, "analysis": {"enum": ["summary", "distribution", "correlation", "groupby"], "type": "string", "default": "summary", "description": "分析类型"}, "columns": {"type": "array", "items": {"type": "string"}, "description": "指定分析的列"}}}',
 '{"type": "object", "properties": {"error": {"type": "string"}, "result": {"type": "object"}, "row_count": {"type": "integer"}}}',
 'low', 1, 60, 0,
 '{"readOnlyHint": true, "openWorldHint": false, "idempotentHint": true, "destructiveHint": false, "version": "1.0.0"}'),

-- 代码审查
('code_review', '代码审查', '审查代码质量：语法错误、安全漏洞、性能问题、最佳实践建议', 'code',
 '{"type": "object", "required": ["code"], "properties": {"code": {"type": "string", "description": "要审查的代码"}, "language": {"type": "string", "description": "编程语言"}, "focus": {"enum": ["security", "performance", "style", "all"], "type": "string", "default": "all", "description": "审查重点"}}}',
 '{"type": "object", "properties": {"error": {"type": "string"}, "issues": {"type": "array", "items": {"type": "object", "properties": {"line": {"type": "integer"}, "severity": {"type": "string"}, "message": {"type": "string"}}}}, "score": {"type": "integer"}}}',
 'low', 1, 30, 0,
 '{"readOnlyHint": true, "openWorldHint": false, "idempotentHint": true, "destructiveHint": false, "version": "1.0.0"}');

-- ============================================
-- 3. 统一更新已有工具的 version
-- ============================================
UPDATE `tool` SET `annotations` = JSON_SET(`annotations`, '$.version', '1.0.1'), `updated_at` = NOW()
WHERE `name` IN ('write_file', 'exec_command', 'spawn_agent', 'execute_code', 'cron_create', 'router_control')
  AND JSON_EXTRACT(`annotations`, '$.version') = '1.0.0';

SELECT CONCAT('Migration v1.0.1 完成: ', COUNT(*), ' 个工具') AS result FROM `tool` WHERE `is_deleted` = 0;
