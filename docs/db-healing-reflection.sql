# 自愈反思记忆表 healing_reflection

> **模块**: Self-Healing Agent (Reflexion 模式)
> **版本**: v1.0
> **创建日期**: 2026-06-20
> **设计依据**: Reflexion 论文 + CrewAI Guardrail 模式 + 2026 行业最佳实践
> **P3C 合规**: ✅ 全部通过

---

## 1. 设计背景

### 1.1 问题

Goal 模式执行子任务时，失败后简单重试，没有从失败中学习。同类错误反复出现。

### 1.2 解决方案

引入 Reflexion 模式——将失败转化为结构化反思，存入记忆系统，下次遇到类似情况时自动注入策略。

### 1.3 核心闭环

```
失败 → 归因(错误类型/触发条件) → 结构化反思 → 存入记忆
                                                ↓
下次执行 ← 检索相关反思 ← 注入 prompt ← 策略调整
```

---

## 2. 表结构

```sql
CREATE TABLE healing_reflection (
    id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    user_id           BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '用户 ID',
    failure_type      VARCHAR(32) NOT NULL DEFAULT '' COMMENT '失败类型: tool_error/guardrail_fail/llm_error/timeout/empty_output/incomplete',
    trigger_cond      VARCHAR(500) NOT NULL DEFAULT '' COMMENT '触发条件',
    what_not_to_do    VARCHAR(500) NOT NULL DEFAULT '' COMMENT '避免的错误',
    suggested_strategy VARCHAR(500) NOT NULL DEFAULT '' COMMENT '建议策略',
    confidence        INT UNSIGNED NOT NULL DEFAULT 70 COMMENT '置信度 0-100',
    scope_tags        JSON NOT NULL DEFAULT (JSON_ARRAY()) COMMENT '作用域标签 ["guardrail","tool_error"]',
    subtask_id        BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '关联子任务 ID',
    subtask_title     VARCHAR(256) NOT NULL DEFAULT '' COMMENT '子任务标题',
    goal_definition   VARCHAR(1000) NOT NULL DEFAULT '' COMMENT '目标描述',
    retry_count       INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '已重试次数',
    was_successful    TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '后续是否成功: 0=否 1=是',
    ttl_seconds       INT UNSIGNED NOT NULL DEFAULT 3600 COMMENT '有效期秒数',
    expired_at        DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00' COMMENT '过期时间',
    is_deleted        TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否删除: 0=正常 1=已删除',
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_healing_reflection_user (user_id),
    INDEX idx_healing_reflection_type (user_id, failure_type),
    INDEX idx_healing_reflection_expired (expired_at),
    INDEX idx_healing_reflection_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自愈反思记忆 Reflexion 模式';
```

---

## 3. 字段说明

### 3.1 核心字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `failure_type` | VARCHAR(32) | 失败类型枚举 | `tool_error` |
| `trigger_cond` | VARCHAR(500) | 触发条件描述 | `子任务"搜索XX"工具调用超时` |
| `what_not_to_do` | VARCHAR(500) | 避免的错误 | `不要在工具失败后直接输出"抱歉"` |
| `suggested_strategy` | VARCHAR(500) | 建议策略 | `工具不可用时基于已有知识降级回答` |
| `confidence` | INT UNSIGNED | 置信度 0-100 | `80` |

### 3.2 关联字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `subtask_id` | BIGINT UNSIGNED | 关联的 Goal 子任务 ID |
| `subtask_title` | VARCHAR(256) | 子任务标题（冗余，方便查询） |
| `goal_definition` | VARCHAR(1000) | 原始目标描述 |

### 3.3 治理字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `scope_tags` | JSON | 作用域标签，防止记忆污染（A 场景反思误伤 B 场景） |
| `retry_count` | INT UNSIGNED | 已重试次数，超过 3 次放弃 |
| `was_successful` | TINYINT UNSIGNED | 这次反思是否最终导致成功，用于评估反思质量 |
| `ttl_seconds` | INT UNSIGNED | 有效期（秒），过期后不再检索 |
| `expired_at` | DATETIME | 过期时间 = created_at + ttl_seconds |

---

## 4. failure_type 枚举值

| 值 | 说明 | 来源 |
|----|------|------|
| `tool_error` | 工具调用失败 | Guardrail 检测 / 工具返回 error |
| `guardrail_fail` | 输出校验失败 | `_guardrail_check_subtask()` |
| `llm_error` | LLM 调用失败 | 超时 / 速率限制 / 异常 |
| `timeout` | 执行超时 | 超过 max_iterations |
| `empty_output` | 空输出 | Guardrail 检测 |
| `incomplete` | 输出不完整 | 承诺性回复无实质内容 |
| `irrelevant` | 输出与目标无关 | Goal 评估器判定 |
| `budget_exceeded` | Token 预算超限 | 不可重试 |

---

## 5. scope_tags 作用域标签

用于防止记忆污染（Reflexion 论文核心治理策略）。

| 标签 | 说明 |
|------|------|
| `guardrail` | Guardrail 校验相关 |
| `tool_failure` | 工具调用失败 |
| `tool_search` | 搜索工具失败 |
| `tool_browse` | 浏览工具失败 |
| `llm` | LLM 调用相关 |
| `timeout` | 超时相关 |
| `rate_limit` | 速率限制 |
| `eval` | Goal 评估相关 |
| `goal_miss` | 目标未达成 |
| `empty_output` | 空输出 |

---

## 6. Redis 短期记忆

除了 MySQL 长期存储，短期反思存入 Redis：

```
Key:   healing:goal:{goal_id}
TTL:   1800 秒（30 分钟）
Value: JSON 数组 [{reflection_1}, {reflection_2}, ...]
```

**生命周期**：
- Goal 开始 → 创建 Redis key
- 子任务失败 → 写入反思到 Redis
- 下次迭代 → 从 Redis 读取反思注入 prompt
- Goal 结束 → TTL 自动过期

---

## 7. 查询场景

### 7.1 检索相关反思（按作用域）

```sql
SELECT failure_type, trigger_cond, what_not_to_do, suggested_strategy, confidence
FROM healing_reflection
WHERE user_id = :user_id
  AND is_deleted = 0
  AND expired_at > NOW()
  AND JSON_CONTAINS(scope_tags, '"guardrail"')
ORDER BY confidence DESC
LIMIT 3;
```

### 7.2 统计反思成功率

```sql
SELECT failure_type,
       COUNT(*) AS total,
       SUM(was_successful) AS successful,
       ROUND(SUM(was_successful) / COUNT(*) * 100, 1) AS success_rate
FROM healing_reflection
WHERE user_id = :user_id AND is_deleted = 0
GROUP BY failure_type;
```

### 7.3 清理过期反思

```sql
UPDATE healing_reflection
SET is_deleted = 1, updated_at = NOW()
WHERE expired_at < NOW() AND is_deleted = 0;
```

---

## 8. P3C 合规检查

| 条款 | 检查项 | 结果 |
|------|--------|------|
| 表名 | 小写字母+数字，非复数，非保留字 | ✅ `healing_reflection` |
| 字段 | 全部 NOT NULL + 默认值 | ✅ |
| 主键 | `BIGINT UNSIGNED AUTO_INCREMENT` | ✅ |
| 软删除 | `is_deleted` `TINYINT UNSIGNED` 0/1 | ✅ |
| 布尔字段 | `was_successful` `TINYINT UNSIGNED` 命名 `is_xxx` 风格 | ✅ |
| 非负字段 | 全部加 `UNSIGNED` | ✅ |
| JSON 默认值 | `DEFAULT (JSON_ARRAY())` | ✅ |
| 索引命名 | `idx_healing_reflection_{字段}` | ✅ |
| 存储引擎 | InnoDB + utf8mb4 | ✅ |
| 外键 | 无（应用层管理） | ✅ |
| varchar 长度 | 最大 1000 < 5000 | ✅ |

---

## 9. 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Goal 模式执行流程                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  model_selector → llm_call → tool_executor              │
│       ↑                              ↓                  │
│       │                    goal_status_updater           │
│       │                         ↓     ↓                 │
│       │              [成功]   [失败]                     │
│       │                 ↓        ↓                      │
│       │          更新子任务  FailureAnalyzer              │
│       │          status=done    ↓                       │
│       │                 ↓    Reflection                  │
│       │                 ↓        ↓                      │
│       │           ┌─────────────────────┐               │
│       │           │   HealingMemory     │               │
│       │           │  ┌──────────────┐   │               │
│       │           │  │ Redis 短期   │   │               │
│       │           │  │ TTL 30min    │   │               │
│       │           │  └──────────────┘   │               │
│       │           │  ┌──────────────┐   │               │
│       │           │  │ MySQL 长期   │   │               │
│       │           │  │ healing_     │   │               │
│       │           │  │ reflection   │   │               │
│       │           │  └──────────────┘   │               │
│       │           └─────────────────────┘               │
│       │                        ↓                        │
│       └──────────── goal_replanner                      │
│                    (注入反思到下轮 prompt)                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```
