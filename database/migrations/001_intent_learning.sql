-- ============================================================
-- 意图学习模块 — 建表 SQL
-- 对齐 MySQL P3C 规范
-- 执行顺序：intent_correction → behavior_pattern → skill_suggestion
-- ============================================================

-- 1. 意图纠正记录
CREATE TABLE IF NOT EXISTS intent_correction (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    original_intent VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '原始意图文本',
    correct_module  VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '纠正后的目标模块',
    user_id         BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '用户 ID',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_intent_correction_user_id (user_id),
    INDEX idx_intent_correction_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='意图纠正记录';

-- 2. 行为模式
CREATE TABLE IF NOT EXISTS behavior_pattern (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    description     VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '模式描述',
    frequency       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '触发频率',
    actions         JSON            NOT NULL COMMENT '动作序列',
    user_id         BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '用户 ID',
    is_solved       TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否已被技能覆盖: 1=是 0=否',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_behavior_pattern_user_id (user_id),
    INDEX idx_behavior_pattern_frequency (frequency)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行为模式';

-- 3. 技能建议
CREATE TABLE IF NOT EXISTS skill_suggestion (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    pattern_id      BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '关联的行为模式 ID',
    name            VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '建议技能名称',
    description     VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '建议描述',
    status          TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态: 0=待处理 1=已接受 2=已忽略',
    user_id         BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '用户 ID',
    ignore_count    INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '连续忽略次数',
    last_feedback   VARCHAR(32)     NOT NULL DEFAULT '' COMMENT '最近反馈: accepted/ignored',
    is_deleted      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 1=是 0=否',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_skill_suggestion_user_id (user_id),
    INDEX idx_skill_suggestion_status (status),
    INDEX idx_skill_suggestion_pattern_id (pattern_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能建议';
