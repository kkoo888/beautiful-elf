-- ============================================================
-- 大模型供应商表 (llm_provider)
-- 规范: MySQL P3C 规约
-- 生成时间: 2026-06-02
-- ============================================================

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
