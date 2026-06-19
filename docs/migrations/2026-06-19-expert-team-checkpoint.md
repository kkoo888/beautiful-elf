# 专家团进化 — SQL 迁移文档

> 执行日期：2026-06-19
> 关联功能：Checkpoint 断点恢复 + 人类介入 + 执行回放

---

## 迁移清单

| # | 文件 | 说明 | 影响表 |
|---|------|------|--------|
| 1 | `add_expert_team_checkpoint.sql` | 新增 `progress_json` 字段 | `expert_team_run` |

---

## 1. 新增执行检查点字段

```sql
-- 文件: backend/migrations/add_expert_team_checkpoint.sql
-- 功能: 专家团执行断点恢复 + 人类审核 + 执行回放

ALTER TABLE expert_team_run
    ADD COLUMN progress_json JSON NOT NULL DEFAULT (JSON_ARRAY())
    COMMENT '执行检查点记录（断点恢复 + 回放）';
```

### 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `progress_json` | JSON | `[]` | 执行检查点数组，每个元素记录一个关键步骤的状态 |

### 数据结构

```json
[
  {
    "step": 1,
    "step_name": "pm_plan_done",
    "data": {
      "assignments": [{"expert_id": 1, "subtask": "..."}],
      "expert_count": 3
    },
    "timestamp": "2026-06-19T22:00:00"
  },
  {
    "step": 4,
    "step_name": "round_1_experts_done",
    "data": {"round": 1, "expert_count": 3},
    "timestamp": "2026-06-19T22:01:30"
  }
]
```

### Step 枚举值

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | INIT | 初始化 |
| 1 | PM_PLAN | PM 分配计划完成 |
| 2 | DEBATE | 辩论轮次完成 |
| 3 | EXPERT_EXECUTING | 专家执行中 |
| 4 | EXPERT_DONE | 专家执行完成 |
| 5 | GUARDRAIL | 质量校验完成 |
| 6 | PM_EVAL | PM 评估完成 |
| 7 | PM_REPORT | PM 汇总报告完成 |
| 8 | COMPLETED | 全部完成 |
| 9 | FAILED | 执行失败 |
| 10 | PAUSED | 暂停等待人类审核 |

### run_status 新增值

| 值 | 说明 | 新增 |
|----|------|------|
| 0 | 待执行 | — |
| 1 | 运行中 | — |
| 2 | 已完成 | — |
| 3 | 失败 | — |
| 4 | 已取消 | — |
| **5** | **暂停等待审核** | ✅ 新增 |

---

## 执行方式

```bash
# 连接数据库后执行
mysql -u <user> -p <database_name> < backend/migrations/add_expert_team_checkpoint.sql
```

## 回滚

```sql
ALTER TABLE expert_team_run DROP COLUMN progress_json;
```
