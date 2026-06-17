-- ============================================================
-- 提炼记忆模块 — 借鉴 Hindsight Observations 架构
-- 生成时间: 2026-06-17
-- 说明: 新建 memory_observation + memory_observation_source 两张表
-- ⚠️ 执行前请先备份数据库!
-- ============================================================

-- ============================================================
-- 1. 提炼记忆表
-- ============================================================
CREATE TABLE IF NOT EXISTS `memory_observation` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`      BIGINT UNSIGNED NOT NULL DEFAULT 0    COMMENT '用户 ID',
  `content`      TEXT            NOT NULL               COMMENT '提炼内容（Markdown）',
  `category`     VARCHAR(32)     NOT NULL DEFAULT 'decisions' COMMENT '分类: decisions/pitfalls/preferences/status',
  `freshness`    VARCHAR(16)     NOT NULL DEFAULT 'new'       COMMENT '新鲜度: new/stable/strengthening/weakening/stale',
  `source_days`  INT UNSIGNED    NOT NULL DEFAULT 0     COMMENT '来源日志天数',
  `is_deleted`   INT UNSIGNED    NOT NULL DEFAULT 0     COMMENT '是否删除: 1=是 0=否',
  `created_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_obs_user`         (`user_id`),
  INDEX `idx_obs_category`     (`user_id`, `category`),
  INDEX `idx_obs_freshness`    (`user_id`, `freshness`),
  INDEX `idx_obs_is_deleted`   (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='提炼记忆表（借鉴 Hindsight Observations）';


-- ============================================================
-- 2. 提炼记忆关联表（多对多：observation ↔ daily log）
-- ============================================================
CREATE TABLE IF NOT EXISTS `memory_observation_source` (
  `id`               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `observation_id`   BIGINT UNSIGNED NOT NULL     COMMENT '→ memory_observation.id',
  `source_memory_id` BIGINT UNSIGNED NOT NULL     COMMENT '→ markdown_memory.id（daily log）',
  `evidence_quote`   VARCHAR(500)    NOT NULL DEFAULT '' COMMENT '从源日志中提取的关键引用',
  `is_deleted`       INT UNSIGNED    NOT NULL DEFAULT 0  COMMENT '是否删除: 1=是 0=否',
  `created_at`       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_obs_src_obs`      (`observation_id`),
  INDEX `idx_obs_src_memory`   (`source_memory_id`),
  INDEX `idx_obs_src_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='提炼记忆关联表（证据溯源）';
