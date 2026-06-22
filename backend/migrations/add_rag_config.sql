-- ============================================================
-- RAG 检索配置表
-- 功能: 管理 RAG 管道的分块、检索、重排序等参数
-- 规范: MySQL P3C
-- 作者: 小希
-- 日期: 2026-06-22
-- ============================================================

CREATE TABLE IF NOT EXISTS rag_config (
    -- 主键: unsigned bigint 自增，单表步长 1
    id              BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT  COMMENT '主键 ID',

    -- ── 分块参数 ──────────────────────────────────────────
    chunk_size          INT UNSIGNED    NOT NULL DEFAULT 2048      COMMENT '分块大小（tokens），推荐 512-4096',
    chunk_overlap       INT UNSIGNED    NOT NULL DEFAULT 256       COMMENT '分块重叠（tokens），推荐 chunk_size 的 10%-15%',

    -- ── 检索参数 ──────────────────────────────────────────
    similarity_top_k    INT UNSIGNED    NOT NULL DEFAULT 10        COMMENT '向量检索返回条数，推荐 5-20',
    bm25_top_n          INT UNSIGNED    NOT NULL DEFAULT 20        COMMENT 'BM25 关键词检索返回条数，推荐 10-50',
    rrf_k               INT UNSIGNED    NOT NULL DEFAULT 60        COMMENT 'RRF 融合参数 k，推荐 30-100',

    -- ── 重排序参数 ────────────────────────────────────────
    rerank_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1        COMMENT '是否启用重排序: 1=启用 0=禁用',
    rerank_top_n        INT UNSIGNED    NOT NULL DEFAULT 5         COMMENT '重排序后保留条数，推荐 3-10',

    -- ── Embedding 参数 ────────────────────────────────────
    embedding_model     VARCHAR(128)    NOT NULL DEFAULT ''        COMMENT 'Embedding 模型名称（空=使用默认）',
    embedding_dimension INT UNSIGNED    NOT NULL DEFAULT 1024      COMMENT 'Embedding 向量维度',

    -- ── 查询改写参数 ──────────────────────────────────────
    query_rewrite_enabled TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '是否启用查询改写: 1=启用 0=禁用',

    -- ── 通用字段（P3C 必备三字段）─────────────────────────
    created_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
    updated_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    PRIMARY KEY (id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = 'RAG 检索配置表';

-- 初始化默认配置（单例模式，只有一条记录）
INSERT INTO rag_config (id, chunk_size, chunk_overlap, similarity_top_k, bm25_top_n, rrf_k,
                        rerank_enabled, rerank_top_n, embedding_model, embedding_dimension,
                        query_rewrite_enabled)
VALUES (1, 2048, 256, 10, 20, 60, 1, 5, '', 1024, 1);

-- ============================================================
-- Agent 可配置参数（存入 setting 表，运行时可热更新）
-- 说明: 这些参数在 agent_service 初始化时从 setting 表读取
--       修改后重启服务生效（restart_required=1）
-- ============================================================

INSERT IGNORE INTO setting (settings_key, key_value, description, restart_required) VALUES ('agent.intent_threshold', '0.75', '意图匹配置信度阈值（0-1），越低越宽松', 1);

INSERT IGNORE INTO setting (settings_key, key_value, description, restart_required)
VALUES ('agent.semantic_cache_threshold', '0.92', '语义缓存命中阈值（0-1），越高越严格', 1);

INSERT IGNORE INTO setting (settings_key, key_value, description, restart_required)
VALUES ('agent.timeout_seconds', '300', 'Agent 全局超时（秒），默认 5 分钟', 1);
