-- ============================================================
-- 内置工具初始化 — 4 个核心工具写入 tool 表
-- 执行前请确认 tool 表已存在
-- ============================================================

INSERT INTO tool (name, display_name, description, module, json_schema, risk_level, is_enabled, is_deleted, created_at, updated_at) VALUES

-- 1. 联网搜索
('web_search', '联网搜索', '搜索互联网获取实时信息，支持关键词搜索，返回标题、链接和摘要', 'builtin',
 '{"type":"object","properties":{"query":{"type":"string","description":"搜索关键词"},"max_results":{"type":"integer","description":"最大结果数","default":5}},"required":["query"]}',
 'low', 1, 0, NOW(), NOW()),

-- 2. 沙箱执行代码
('execute_code', '代码执行', '在 Docker 沙箱中执行代码（隔离环境，10 秒超时），支持 Python 和 JavaScript', 'builtin',
 '{"type":"object","properties":{"language":{"type":"string","enum":["python","javascript"],"description":"编程语言"},"code":{"type":"string","description":"要执行的代码"}},"required":["language","code"]}',
 'high', 1, 0, NOW(), NOW()),

-- 3. 读取文件
('read_file', '读取文件', '读取工作空间中的文件内容，支持文本文件，单文件上限 1MB', 'builtin',
 '{"type":"object","properties":{"path":{"type":"string","description":"文件路径（相对于工作空间根目录）"}},"required":["path"]}',
 'low', 1, 0, NOW(), NOW()),

-- 4. 数据库查询
('query_database', '数据库查询', '执行只读 SQL 查询（仅 SELECT），自动添加 LIMIT 100 防止全表扫描', 'builtin',
 '{"type":"object","properties":{"sql":{"type":"string","description":"SQL 查询语句（仅 SELECT）"}},"required":["sql"]}',
 'medium', 1, 0, NOW(), NOW())

ON DUPLICATE KEY UPDATE
  display_name = VALUES(display_name),
  description = VALUES(description),
  json_schema = VALUES(json_schema),
  risk_level = VALUES(risk_level),
  updated_at = NOW();
