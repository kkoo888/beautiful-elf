# rag_config 表 — RAG 检索配置

## 表说明

| 字段 | 说明 |
|------|------|
| 表名 | `rag_config` |
| 引擎 | InnoDB |
| 字符集 | utf8mb4 / utf8mb4_unicode_ci |
| 用途 | 管理 RAG 检索管道的分块、检索、重排序等参数 |
| 设计模式 | 单例模式（id=1），只有一条记录 |

## 建表语句

```sql
CREATE TABLE IF NOT EXISTS rag_config (
    id              BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT  COMMENT '主键 ID',
    chunk_size          INT UNSIGNED    NOT NULL DEFAULT 2048      COMMENT '分块大小（tokens），推荐 512-4096',
    chunk_overlap       INT UNSIGNED    NOT NULL DEFAULT 256       COMMENT '分块重叠（tokens），推荐 chunk_size 的 10%-15%',
    similarity_top_k    INT UNSIGNED    NOT NULL DEFAULT 10        COMMENT '向量检索返回条数，推荐 5-20',
    bm25_top_n          INT UNSIGNED    NOT NULL DEFAULT 20        COMMENT 'BM25 关键词检索返回条数，推荐 10-50',
    rrf_k               INT UNSIGNED    NOT NULL DEFAULT 60        COMMENT 'RRF 融合参数 k，推荐 30-100',
    rerank_enabled      TINYINT UNSIGNED NOT NULL DEFAULT 1        COMMENT '是否启用重排序: 1=启用 0=禁用',
    rerank_top_n        INT UNSIGNED    NOT NULL DEFAULT 5         COMMENT '重排序后保留条数，推荐 3-10',
    embedding_model     VARCHAR(128)    NOT NULL DEFAULT ''        COMMENT 'Embedding 模型名称（空=使用默认）',
    embedding_dimension INT UNSIGNED    NOT NULL DEFAULT 1024      COMMENT 'Embedding 向量维度',
    query_rewrite_enabled TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '是否启用查询改写: 1=启用 0=禁用',
    created_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
    updated_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = 'RAG 检索配置表';
```

## 字段说明

| 字段 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|---------|------|
| `id` | BIGINT UNSIGNED | 自增 | — | 主键，单表自增步长 1 |
| `chunk_size` | INT UNSIGNED | 2048 | 128-8192 | 分块大小（tokens）。越大保留上下文越多，但检索精度可能下降 |
| `chunk_overlap` | INT UNSIGNED | 256 | 0-2048 | 分块重叠（tokens）。防止语义在边界处断裂，推荐 chunk_size 的 10%-15% |
| `similarity_top_k` | INT UNSIGNED | 10 | 1-50 | 向量语义检索返回的最大条数 |
| `bm25_top_n` | INT UNSIGNED | 20 | 1-100 | BM25 关键词检索返回的最大条数 |
| `rrf_k` | INT UNSIGNED | 60 | 1-200 | Reciprocal Rank Fusion 融合参数 k。越大结果越平滑 |
| `rerank_enabled` | TINYINT UNSIGNED | 1 | 0/1 | 是否启用 Cross-Encoder 重排序精排 |
| `rerank_top_n` | INT UNSIGNED | 5 | 1-20 | 重排序后保留的条数 |
| `embedding_model` | VARCHAR(128) | '' | — | Embedding 模型名称（空=使用系统默认） |
| `embedding_dimension` | INT UNSIGNED | 1024 | 64-4096 | Embedding 向量维度 |
| `query_rewrite_enabled` | TINYINT UNSIGNED | 1 | 0/1 | 是否启用 LLM 查询改写（口语化→精确检索查询） |
| `created_at` | DATETIME | CURRENT_TIMESTAMP | — | 创建时间 |
| `updated_at` | DATETIME | CURRENT_TIMESTAMP ON UPDATE | — | 更新时间 |

## P3C 合规检查

| 规则 | 状态 | 说明 |
|------|------|------|
| 表名小写字母 + 下划线 | ✅ | `rag_config` |
| 表名不以数字开头 | ✅ | — |
| 表名不用复数 | ✅ | — |
| 表名不用保留字 | ✅ | — |
| 所有字段 NOT NULL | ✅ | — |
| 必备三字段 (id, created_at, updated_at) | ✅ | — |
| id unsigned bigint autoincrement | ✅ | — |
| 布尔字段 is_xxx 命名 | ✅ | `rerank_enabled`, `query_rewrite_enabled` |
| 布尔字段 unsigned tinyint | ✅ | — |
| 非负字段 unsigned | ✅ | 所有 INT UNSIGNED |
| 无 NULL 字段 | ✅ | 全部 NOT NULL + 默认值 |
| 无 float/double | ✅ | — |
| 索引 | — | 单例模式，主键索引足够 |

## 初始化数据

```sql
INSERT INTO rag_config (id, chunk_size, chunk_overlap, similarity_top_k, bm25_top_n, rrf_k,
                        rerank_enabled, rerank_top_n, embedding_model, embedding_dimension,
                        query_rewrite_enabled)
VALUES (1, 2048, 256, 10, 20, 60, 1, 5, '', 1024, 1);
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/knowledge/rag-config` | 获取配置 |
| PUT | `/api/v1/knowledge/rag-config` | 更新配置 |

## 参数调优建议

| 场景 | chunk_size | chunk_overlap | similarity_top_k | rerank_enabled |
|------|-----------|---------------|-------------------|----------------|
| 快速原型 | 512 | 64 | 5 | false |
| 通用文档问答 | 2048 | 256 | 10 | true |
| 长文档精确检索 | 4096 | 512 | 15 | true |
| 法律/医学专业 | 1024 | 128 | 20 | true |
