-- ============================================================
-- Tool 表 v2 迁移 SQL
-- 对齐 MCP 2025-06-18 + OpenAI Function Calling 最新规范
-- 日期: 2026-06-24
-- ============================================================
--
-- 变更说明:
--   1. 移除 `version` 独立字段
--      - MCP 规范中工具没有顶级 version 字段
--      - 版本信息迁入 annotations.version（JSON 内）
--   2. 新增 `strict_mode` 字段
--      - OpenAI strict 模式，强制 LLM 输出严格符合 JSON Schema
--      - 高风险工具（exec_command / execute_code / query_database）默认启用
--   3. annotations 保持 NOT NULL（P3C 规约）
--
-- 执行顺序: Step 1 → Step 2 → Step 3 → Step 4（不可逆，建议先备份）
-- 回滚方案: 见文件末尾
--
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ── Step 1: 新增 strict_mode 字段 ──────────────────────────
ALTER TABLE `tool`
  ADD COLUMN `strict_mode` tinyint UNSIGNED NOT NULL DEFAULT 0
  COMMENT 'OpenAI strict 模式: 1=启用 0=禁用'
  AFTER `timeout_seconds`;

-- ── Step 2: 将 version 值迁移到 annotations JSON 中 ────────
UPDATE `tool`
SET `annotations` = JSON_SET(
  IFNULL(`annotations`, '{}'),
  '$.version',
  IFNULL(`version`, '1.0.0')
);

-- ── Step 3: 删除 version 字段 ──────────────────────────────
ALTER TABLE `tool`
  DROP COLUMN `version`;

-- ── Step 4: 高风险工具启用 strict_mode ─────────────────────
UPDATE `tool`
SET `strict_mode` = 1
WHERE `name` IN ('exec_command', 'execute_code', 'query_database');

SET FOREIGN_KEY_CHECKS = 1;

-- ── 验证 ───────────────────────────────────────────────────
SELECT
  id,
  name,
  module,
  risk_level,
  strict_mode,
  JSON_UNQUOTE(JSON_EXTRACT(`annotations`, '$.version')) AS ann_version
FROM `tool`
WHERE `is_deleted` = 0
ORDER BY id;


-- ============================================================
-- 回滚 SQL（如需恢复 version 字段）
-- ============================================================
--
-- ALTER TABLE `tool`
--   ADD COLUMN `version` varchar(32) NOT NULL DEFAULT '1.0.0'
--   COMMENT '工具版本号 (FastMCP v3)'
--   AFTER `is_enabled`;
--
-- UPDATE `tool`
-- SET `version` = IFNULL(
--   JSON_UNQUOTE(JSON_EXTRACT(`annotations`, '$.version')),
--   '1.0.0'
-- );
--
-- ALTER TABLE `tool`
--   DROP COLUMN `strict_mode`;
--
