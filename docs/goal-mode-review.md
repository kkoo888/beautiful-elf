# Goal 模式全流程 Review + 前沿技术对比

> 审查时间: 2026-06-20
> 审查范围: `backend/app/agent/engine.py` Goal 模式完整链路
> 修复项: P0-P4（5 个 bug，已全部修复）

---

## 一、当前架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     Goal 模式执行流程                            │
│                                                                  │
│  iter=0 (规划)                                                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ model_   │───▸│ intent_  │───▸│ context_ │───▸│ llm_call │   │
│  │ selector │    │ router   │    │ builder  │    │ (plan)   │   │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘   │
│                                                       │          │
│       ┌───────────────────────────────────────────────┘          │
│       ▼                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐               │
│  │ evaluator│───▸│ memory_  │───▸│ goal_status_ │               │
│  │ (skip)   │    │ saver    │    │ updater(0)   │               │
│  └──────────┘    │ (skip)   │    └──────┬───────┘               │
│                  └──────────┘           │                        │
│                                         ▼                        │
│                                 ┌──────────────┐                 │
│                                 │ goal_        │                 │
│                                 │ replanner    │───▸ model_      │
│                                 │ (iter+1)     │    selector     │
│                                 └──────────────┘    (loop)       │
│                                                                  │
│  iter=1+ (执行)                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │
│  │ llm_call │───▸│ tool_    │───▸│ llm_call │                   │
│  │ (exec)   │    │ executor │    │ (result) │                   │
│  └──────────┘    └──────────┘    └────┬─────┘                   │
│                                       │                          │
│       ┌───────────────────────────────┘                          │
│       ▼                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │ evaluator│───▸│ goal_status_ │───▸│ goal_        │           │
│  │ (skip)   │    │ updater      │    │ replanner    │           │
│  └──────────┘    │ (guardrail)  │    └──────┬───────┘           │
│                  └──────────────┘           │                    │
│                                             ▼                    │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ _after_goal_replan:                                   │       │
│  │   achieved → memory_saver → END                       │       │
│  │   in_progress → model_selector (loop)                 │       │
│  │   failed/budget_exceeded → END                        │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、已修复的 5 个 Bug

| # | 严重度 | 问题 | 修复 |
|---|--------|------|------|
| P0 | 🔴 Critical | `progress_text` / `current_task_text` 未定义 → NameError 崩溃 | 在 f-string 前定义变量 |
| P1 | 🟡 High | iter=0 guardrail 误判：计划文本被当成任务执行结果 | iter=0 跳过 guardrail，直接激活首个子任务 |
| P2 | 🟡 High | iter=0→1 过渡：guardrail 错误标记第一个子任务为 done | 同 P1，合并修复 |
| P3 | 🟢 Low | `_after_goal_replan` 达成时走 `goal_evaluator`，浪费 LLM 调用 | 改为直接走 `memory_saver` |
| P4 | 🔴 Critical | `_after_memory` 未检查终态 → `achieved → goal_status_updater → goal_replanner → achieved → memory_saver` 死循环 | 终态直接返回 END |

---

## 三、当前架构的优势

1. **Plan-Execute 分离** — iter=0 纯规划，iter=1+ 纯执行，职责清晰
2. **DAG 依赖管理** — `_get_next_pending_subtask` / `_get_parallel_ready_tasks` 支持拓扑排序
3. **Self-Healing 闭环** — 失败 → 结构化反思 → Redis/MySQL 存储 → prompt 注入 → 重试
4. **Guardrail 校验** — 格式校验（空输出、承诺性回复、失败标记）+ 反思
5. **LoopDetector** — 防止同一子任务无限循环
6. **Token 预算控制** — 防止 token 耗尽
7. **Streaming 可视化** — 每个步骤都有 writer 事件

---

## 四、问题 & 优化方向（按优先级排序）

### 🔴 P0: 解析脆弱性 — 正则匹配 [目标拆解]

**现状**: `_parse_goal_subtasks` 用正则从 LLM 自由文本中解析子任务列表。

**问题**:
- LLM 输出格式不稳定（少一个空格、换行符不同 → 解析失败）
- 解析失败 → `goal_subtasks` 为空 → replanner 判定 `failed`
- 前端依赖 `[目标拆解]` 格式 → 耦合

**前沿对比**:
- **LangChain Structured Output**: `llm.with_structured_output(SubtaskPlan)` → 100% 可靠解析
- **Instructor 库**: 强制 LLM 输出符合 JSON Schema 的结构化数据
- **Claude Tool Use / GPT Function Calling**: 用 tool_calls 格式输出计划

**建议**: 
```python
class SubtaskPlan(BaseModel):
    subtasks: list[SubtaskItem]
    
class SubtaskItem(BaseModel):
    id: int
    title: str
    description: str
    dependencies: list[int] = []
    
structured_llm = llm.with_structured_output(SubtaskPlan)
plan = await structured_llm.ainvoke(planning_messages)
```

---

### 🔴 P1: 缺乏动态重规划（Dynamic Replanning）

**现状**: 失败后只是重试同一子任务（最多 2 次），不调整计划。

**问题**:
- 子任务 A 持续失败 → 但后续任务 B、C 依赖 A → 全部卡死
- 没有能力「跳过失败任务，先做能做的」
- 没有能力「重新规划整个计划」

**前沿对比**:
- **LangGraph Plan-and-Execute 官方**: 有 `replan` 节点，失败时让 LLM 重新生成整个计划
- **LLMCompiler (2024)**: DAG 编排器，任务失败时动态调整后续依赖
- **ADaPT (2024)**: As-Needed Decomposition and Planning，递归分解，失败时细化子任务

**建议**: `goal_replanner` 失败时调用 LLM 重新生成计划，而不是简单重试：
```python
replan_prompt = f"""原目标: {goal_def}
已完成: {done_tasks}
失败任务: {failed_tasks} (原因: {failure_reasons})
请重新规划剩余步骤，可以调整策略、跳过不可行的任务、或分解失败任务为更小的子任务。"""
```

---

### 🟡 P2: 每轮只执行一个子任务

**现状**: 每次迭代只执行一个子任务（`_get_next_pending_subtask` 返回单个）。

**问题**: 无依赖的子任务可以并行执行，但当前串行处理。

**前沿对比**:
- **LLMCompiler**: 并行执行无依赖任务，`asyncio.gather`
- **AutoGen**: GroupChat 模式，多个 Agent 并行工作
- **CrewAI**: Process.parallel 模式

**建议**: `_get_parallel_ready_tasks` 已经支持返回多个，但 `llm_call` 只处理一个。需要：
1. 并行执行多个无依赖子任务
2. 或者让 LLM 在一次调用中处理多个子任务

---

### 🟡 P3: 缺乏中间结果积累（Working Memory）

**现状**: 每个子任务独立执行，不感知前序任务的结果。

**问题**:
- 子任务 1 搜索到的信息 → 子任务 2 无法使用
- 每个子任务都从零开始 → 重复工作

**前沿对比**:
- **Voyager (2023)**: Skill Library — 成功的执行模式可复用
- **Reflexion**: 经验累积 → 下轮注入
- **Generative Agents**: 情景记忆 + 反思记忆 + 工作记忆三层架构

**建议**: 在 State 中增加 `goal_working_memory` 字段：
```python
goal_working_memory: list[dict]  # [{task_id, task_title, result_summary, tool_outputs}]
```
每个子任务完成后，将结果摘要存入 working memory，后续子任务的 prompt 注入：
```
## 前序任务结果
- 任务1「搜索公司信息」: 找到 Loop Engineering，总部旧金山...
- 任务2「分析技术栈」: 使用 Python + LangGraph...
```

---

### 🟡 P4: Guardrail 只做格式校验，无语义校验

**现状**: `_guardrail_check_subtask` 只检查长度、失败标记、承诺性回复。

**问题**:
- 子任务要求「搜索公司信息」，但 LLM 输出了一段关于天气的内容 → 格式通过，语义不通过
- 没有检查输出是否真的完成了子任务

**前沿对比**:
- **Guardrails AI**: Pydantic + LLM 双层校验
- **NeMo Guardrails (NVIDIA)**: 规则 + LLM 混合校验
- **expert_team/guardrail.py**: 项目内已有语义校验实现（`validate_output`）

**建议**: 复用已有的 `expert_team/guardrail.py` 的 `validate_output`：
```python
# 格式校验（快，零成本）→ 语义校验（LLM，仅在格式通过后）
if format_passed:
    semantic_result = await validate_output(
        subtask=current_subtask["title"],
        output=answer_text,
    )
```

---

### 🟢 P5: 成本预估过于粗略

**现状**: `goal_replanner` 用 `avg_tokens * remaining_tasks` 估算。

**问题**: 不同子任务复杂度差异大，平均值无意义。

**建议**: 
- 按子任务类型加权（搜索类 ~2000 tokens，分析类 ~5000 tokens）
- 基于历史执行数据动态调整

---

### 🟢 P6: 缺乏执行质量指标

**现状**: 只有 `achieved/failed/budget_exceeded` 三种终态。

**建议**: 增加执行质量指标：
- `plan_accuracy`: 初始计划 vs 实际执行的偏差度
- `execution_efficiency`: 成功子任务数 / 总迭代数
- `token_efficiency`: 有效 token / 总 token
- `failure_recovery_rate`: 从失败中恢复的比例

---

## 五、进化路线图

### Phase 1: 结构化 + 可靠性（1-2 周）
- [ ] 结构化输出替代正则解析（P0）
- [ ] 复用 `expert_team/guardrail.py` 语义校验（P4）
- [ ] `_after_goal_replan` 达成时跳过 evaluator（P3 ✅ 已修）

### Phase 2: 智能重规划（2-3 周）
- [ ] 动态重规划：失败时让 LLM 重新生成计划（P1）
- [ ] Working Memory：子任务间结果传递（P3）
- [ ] 任务跳过：失败子任务不影响后续可执行任务

### Phase 3: 并行 + 效率（3-4 周）
- [ ] 并行执行无依赖子任务（P2）
- [ ] 成本预估优化（P5）
- [ ] 执行质量指标（P6）

### Phase 4: 前沿技术集成（长期）
- [ ] MCTS/Tree Search 探索多条执行路径
- [ ] Skill Library：成功模式复用（Voyager 模式）
- [ ] 自适应规划：根据任务复杂度动态选择 Plan-and-Execute vs ReAct

---

## 六、总结

当前 Goal 模式的架构基础扎实（Plan-Execute 分离 + Self-Healing + DAG），在行业内属于 **中上水平**。

核心差距在于：
1. **解析可靠性** — 正则 vs 结构化输出（差一个时代）
2. **重规划能力** — 简单重试 vs 动态重规划（实用性差距）
3. **并行执行** — 串行 vs DAG 并行（效率差距）

Phase 1 的投入产出比最高，建议优先推进。
