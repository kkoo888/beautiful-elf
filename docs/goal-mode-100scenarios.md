# Goal 模式 100 场景推演 + 进化方向

> 审查时间: 2026-06-20
> 审查范围: engine.py → nodes.py → goal_nodes.py → goal_helpers.py 全链路
> 方法: 逐条代码路径理论推断，不运行代码

---

## 一、完整流程图

```
用户输入 → model_selector → intent_router → context_builder → llm_call
                                                          ↓
                                              ┌─── iterations==0 (规划) ───┐
                                              │  结构化输出 SubtaskPlan    │
                                              │  返回 goal_subtasks        │
                                              └────────────────────────────┘
                                                          ↓
                                              ┌─── iterations>0 (执行) ────┐
                                              │  ReAct prompt + 工具绑定   │
                                              │  tool_choice=required      │
                                              └────────────────────────────┘
                                                          ↓
                                              ┌─── _should_use_tools ──────┐
                                              │  tool_calls → tool_executor│
                                              │  无 tools → evaluator      │
                                              └────────────────────────────┘
                                                          ↓
                                              ┌─── evaluator ──────────────┐
                                              │  Goal: 结构化质量检查      │
                                              │  普通: LLM-as-Judge       │
                                              └────────────────────────────┘
                                                          ↓
                                              ┌─── memory_saver ───────────┐
                                              │  Goal 中间轮: 跳过         │
                                              │  终态: 正常保存            │
                                              └────────────────────────────┘
                                                          ↓
                                              ┌─── goal_status_updater ────┐
                                              │  iter=0: 激活首批任务      │
                                              │  iter>0: guardrail校验     │
                                              │  → done/failed/retry       │
                                              └────────────────────────────┘
                                                          ↓
                                              ┌─── goal_replanner ─────────┐
                                              │  全部done → achieved       │
                                              │  有failed → 动态重规划     │
                                              │  超限 → failed/budget      │
                                              └────────────────────────────┘
                                                          ↓
                                              ┌─── 路由 ──────────────────┐
                                              │  achieved → memory_saver   │
                                              │  in_progress → model_sel   │
                                              │  failed/budget → END       │
                                              └────────────────────────────┘
```

---

## 二、100 场景推演

### A. 规划阶段（iter=0）— 15 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 1 | 正常规划 3-8 个子任务 | llm_call → SubtaskPlan → goal_subtasks | ✅ 全 pending，进入 status_updater | OK |
| 2 | LLM 返回空 subtasks 列表 | plan_result.subtasks=[] → parsed=[] | ✅ 返回 goal_status: "failed" | OK |
| 3 | LLM 抛异常（超时/限流） | except → 返回 goal_status: "failed" | ✅ 正确终止 | OK |
| 4 | 目标校验失败（过短） | _validate_goal_definition → False | ✅ 返回 is_error: True | OK |
| 5 | 目标校验失败（过长 >2000字） | _validate_goal_definition → False | ✅ 返回 is_error: True | OK |
| 6 | 目标校验失败（纯标点） | _validate_goal_definition → meaningful<5 | ✅ 返回 is_error: True | OK |
| 7 | 只规划出 1 个子任务 | parsed=[{id:1}] | ✅ 单任务 DAG | OK |
| 8 | 规划出 8 个子任务 | parsed=[{id:1}..{id:8}] | ✅ 多任务 | OK |
| 9 | 所有子任务无依赖 | dependencies=[] | ✅ 全部可并行 | OK |
| 10 | 链式依赖 1→2→3 | dependencies 逐级 | ✅ 顺序执行 | OK |
| 11 | 循环依赖 1→2, 2→1 | _get_next_pending: all(d in done_ids) 永不满足 | ⚠️ 永远 pending | **P2** |
| 12 | 依赖不存在的 ID（依赖 99） | all(d in done_ids) 永不满足 | ⚠️ 同上 | **P2** |
| 13 | LLM 返回非 SubtaskPlan 格式 | structured_output 强制校验 → except | ✅ 走异常路径 | OK |
| 14 | LLM 返回子任务 id=0 | id=0 是合法 int | ✅ 正常工作 | OK |
| 15 | LLM 返回重复 id | 多个 id=1 | ⚠️ _update_subtask_status 只更新第一个 | **P3** |

### B. 执行阶段 — 正常路径 — 15 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 16 | LLM 返回纯文本（无 tool_calls） | _should_use_tools → "finish" → evaluator | ✅ 正常 | OK |
| 17 | LLM 返回 tool_calls | _should_use_tools → "use_tools" → tool_executor | ✅ 执行工具 | OK |
| 18 | LLM 返回 text + tool_calls | tool_calls 非空 → "use_tools" | ✅ 工具优先 | OK |
| 19 | LLM 返回空内容 | response.content="" → final_answer="" | ✅ evaluator 会处理 | OK |
| 20 | LLM 返回超长内容（>5000字） | content 正常传递 | ✅ working_memory 截断 200 字 | OK |
| 21 | 工具执行成功 | tool_executor → 成功结果 → llm_call | ✅ 正常 | OK |
| 22 | 工具执行失败（单个） | ErrorContract → 熔断器记录 | ✅ LLM 降级回答 | OK |
| 23 | 工具执行失败（全部） | 所有工具失败 → LLM 基于知识回答 | ✅ 降级 | OK |
| 24 | 工具需要审批（HIGH 风险） | interrupt → 等待用户确认 | ✅ HITL | OK |
| 25 | 用户批准工具执行 | _after_approval → "approved" → llm_call | ✅ 继续 | OK |
| 26 | 用户拒绝工具执行 | _after_approval → "rejected" → memory_saver | ✅ 终止 | OK |
| 27 | 连续 10 轮工具调用 | _should_use_tools: iterations>=10 → "finish" | ✅ 强制结束 | OK |
| 28 | LLM 调用超时 | except → error final_answer | ✅ evaluator 处理 | OK |
| 29 | tool_choice=required 但模型不支持 | bind_tools 异常 | ❌ **未捕获异常** | **P0** |
| 30 | 上轮工具失败 → 降级为 auto | _tool_degraded=True → tool_choice="auto" | ✅ 允许自行回答 | OK |

### C. 工具调用细节 — 10 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 31 | 熔断器 closed → 正常执行 | _circuit_breaker.is_available → True | ✅ | OK |
| 32 | 熔断器 open → 快速失败 | is_available → False → ErrorContract | ✅ | OK |
| 33 | 熔断器 half-open → 试探恢复 | is_available → True → 执行 | ✅ | OK |
| 34 | ToolNode 并行执行 3 个工具 | asyncio.gather | ✅ | OK |
| 35 | ToolNode 异常 → 降级逐个执行 | except → 逐个 try/except | ✅ | OK |
| 36 | 单个工具降级执行也失败 | tool_err → ErrorContract | ✅ | OK |
| 37 | 工具返回 result=None | _format_tool_result_json → ErrorContract | ✅ | OK |
| 38 | 工具返回 result=dict | json.dumps | ✅ | OK |
| 39 | 工具返回 result=list | json.dumps | ✅ | OK |
| 40 | tool_call_id 缺失 | tool_call_id="" or "unknown" | ✅ 不影响 | OK |

### D. Evaluator 评估 — 15 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 41 | Goal 模式 + 有 LLM + 有 final_answer | 结构化评估 → evaluation | ✅ | OK |
| 42 | Goal 模式 + 无 LLM | return goal_mode_skip | ✅ 跳过 | OK |
| 43 | Goal 模式 + 无 final_answer | return goal_mode_skip | ✅ 跳过 | OK |
| 44 | Goal 模式 + LLM 评估异常 | except → goal_mode_skip | ✅ 降级 | OK |
| 45 | Goal 模式 + 评估通过 (score>=6) | evaluation.passed=True | ✅ | OK |
| 46 | Goal 模式 + 评估未通过 (score<6) | evaluation.passed=False | ✅ status_updater 处理 | OK |
| 47 | 普通模式 + LLM-as-Judge 通过 | score>=6 → "pass" | ✅ | OK |
| 48 | 普通模式 + LLM-as-Judge 未通过 | score<6, 有 final_answer → "pass" | ✅ 放行 | OK |
| 49 | 普通模式 + 评估 score<4 | 替换为兜底回答 | ✅ | OK |
| 50 | 普通模式 + LLM 返回 None | 降级规则评估 | ✅ | OK |
| 51 | 普通模式 + LLM 异常 | 降级规则评估 | ✅ | OK |
| 52 | 普通模式 + 无 final_answer | passed=False, score=0 | ✅ | OK |
| 53 | 普通模式 + 回答过短 (<10字) | 规则评估 → score=2 | ✅ | OK |
| 54 | 普通模式 + 包含"服务不可用" | 规则评估 → score=2 | ✅ | OK |
| 55 | Goal 模式评估用 eval_prompt 格式 | 与普通模式不同（简化版） | ⚠️ 可能评分标准不一致 | **P3** |

### E. Status Updater — 20 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 56 | iterations=0 → reset loop_detector | _loop_detector.reset() | ✅ | OK |
| 57 | iterations=0 → 激活首批并行任务 | _get_parallel_ready_tasks → in_progress | ✅ | OK |
| 58 | iterations=0 + 无子任务 | return {} | ✅ | OK |
| 59 | iterations>0 + 有 in_progress 任务 | 取第一个 in_progress | ✅ | OK |
| 60 | iterations>0 + 无 in_progress，有 pending+deps满足 | 自动激活 | ✅ | OK |
| 61 | iterations>0 + 无 in_progress，无 pending+deps满足 | current_subtask=None → 跳过 guardrail | ✅ | OK |
| 62 | evaluator passed + guardrail passed | → done | ✅ | OK |
| 63 | evaluator failed + retry_count<2 | → retry (保持 in_progress) | ✅ | OK |
| 64 | evaluator failed + retry_count>=2 | → failed | ✅ | OK |
| 65 | guardrail 格式校验失败 | → failed + self-healing | ✅ | OK |
| 66 | guardrail 语义校验失败 | → failed + self-healing | ✅ | OK |
| 67 | guardrail 语义校验异常 | 降级为仅格式校验 | ✅ | OK |
| 68 | LoopDetector 连续 3 次失败 | is_looping → True | ⚠️ 只记录，无强制跳过 | **P3** |
| 69 | 任务完成后激活下一批并行任务 | _get_parallel_ready_tasks | ✅ | OK |
| 70 | Working Memory 累积成功结果 | new_wm_entries.append | ✅ | OK |
| 71 | Working Memory 累积失败结果 | new_wm_entries.append (success=False) | ✅ | OK |
| 72 | current_tools_used 为空 | tools_used=[] | ✅ 不影响 | OK |
| 73 | _content_to_str 处理 None | 返回 "" | ✅ | OK |
| 74 | _content_to_str 处理 list[dict] | 提取 text 拼接 | ✅ | OK |
| 75 | 语义校验 LLM 缓存失效 | global _semantic_llm_cache | ⚠️ 缓存跨请求共享 | **P2** |

### F. Replanner — 20 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 76 | 全部 done → achieved | done_count == total | ✅ | OK |
| 77 | Token 超预算 → budget_exceeded | tokens_used >= token_budget | ✅ | OK |
| 78 | 超最大迭代 → failed | iterations >= max_iterations | ✅ | OK |
| 79 | 有 failed + LLM 重规划成功 | GoalReplanResult → new_subtasks | ✅ | OK |
| 80 | 有 failed + LLM 重规划异常 | except → 降级简单重试 | ✅ | OK |
| 81 | 降级重试 + retry_count<2 | 重置为 pending | ✅ | OK |
| 82 | 降级重试 + retry_count>=2 | 保持 failed | ✅ | OK |
| 83 | 无 pending + 无 in_progress + done<total | → failed | ✅ 所有任务卡住 | OK |
| 84 | 有 in_progress 任务 | → in_progress 继续 | ✅ | OK |
| 85 | 有 pending + 有 done | → in_progress 继续 | ✅ | OK |
| 86 | 重规划产生新子任务 | 合并 done + new | ✅ | OK |
| 87 | 重规划依赖重映射 | max_id + d 偏移 | ✅ | OK |
| 88 | 重规划依赖引用已完成任务 | d > len(subtasks) → 保持原 ID | ✅ | OK |
| 89 | 重规划产生空 subtasks | new_subtasks 只有 done | ⚠️ done_count==total → achieved | **P3** |
| 90 | 重规划 LLM 返回异常格式 | structured_output 校验 → except | ✅ 降级 | OK |
| 91 | Self-Healing 存储失败 | except → 跳过 | ✅ 不影响主流程 | OK |
| 92 | Self-Healing mark_successful 失败 | except → 跳过 | ✅ | OK |
| 93 | avg_tokens 计算除零 | max(done_count, 1) | ✅ 已处理 | OK |
| 94 | estimated_remaining 未使用 | 仅日志 | ℹ️ 预留字段 | OK |
| 95 | history 累积过长 | goal_history 不断追加 | ⚠️ 可能膨胀 | **P3** |

### G. 路由 & 终态 — 5 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 96 | achieved → memory_saver → _after_memory | goal_status=achieved → END | ✅ | OK |
| 97 | failed → _after_goal_replan → END | goal_status=failed → END | ✅ | OK |
| 98 | budget_exceeded → END | → END | ✅ | OK |
| 99 | in_progress → model_selector | → 重新执行 | ✅ | OK |
| 100 | goal_status 字段缺失 | status="" → _after_memory: 非终态 → status_updater | ⚠️ 可能循环 | **P2** |

---

## 三、发现的问题汇总

### 🔴 P0: 硬编码 tool_choice="required" — 不兼容所有模型

**位置**: nodes.py `_make_llm_caller`

**问题**: `tool_choice="required"` 不是所有 LLM 都支持。DeepSeek、通义千问等国产模型可能不支持此参数，导致 `bind_tools` 异常。

**影响**: Goal 模式执行阶段直接崩溃。

**修复**: 
```python
try:
    current_llm = current_base_llm.bind_tools(tool_objects, tool_choice="required")
except (ValueError, NotImplementedError):
    current_llm = current_base_llm.bind_tools(tool_objects)
    logger.warning("[llm_call] tool_choice=required 不支持，降级为 auto")
```

---

### 🔴 P1: LoopDetector 全局单例 — 请求间状态泄漏

**位置**: goal_helpers.py `_loop_detector = LoopDetector()`

**问题**: `_loop_detector` 是模块级单例，所有请求共享同一个实例。请求 A 记录了失败历史，会影响请求 B 的循环检测判断。

**影响**: 并发场景下误判循环 → 子任务被错误跳过。

**修复**: 
```python
# 在 goal_status_updater 中按 conversation_id 隔离
# 方案1: 每次从 state 获取/重建
# 方案2: 用 dict[conversation_id, LoopDetector] 做隔离
_loop_detectors: dict[int, LoopDetector] = {}

def _get_loop_detector(conversation_id: int) -> LoopDetector:
    if conversation_id not in _loop_detectors:
        _loop_detectors[conversation_id] = LoopDetector()
    return _loop_detectors[conversation_id]
```

---

### 🔴 P2: 语义校验 LLM 缓存跨请求共享 — 模型不一致

**位置**: goal_helpers.py `_semantic_llm_cache = None`

**问题**: `_semantic_llm_cache` 是模块级变量。请求 A 用 GPT-4o 缓存了 `with_structured_output`，请求 B 可能用 DeepSeek，但仍然使用 GPT-4o 的缓存实例。

**影响**: 
1. 模型路由不生效（语义校验总是用第一个请求的模型）
2. 如果第一个请求的 LLM 实例已关闭，后续请求会报错

**修复**:
```python
# 按 LLM 实例哈希缓存
_semantic_llm_caches: dict[int, Any] = {}

def _get_semantic_llm(llm):
    key = id(llm)
    if key not in _semantic_llm_caches:
        from app.agent.structured_schemas import SemanticSubtaskValidation
        _semantic_llm_caches[key] = llm.with_structured_output(SemanticSubtaskValidation)
    return _semantic_llm_caches[key]
```

---

### 🟡 P3: 循环依赖 / 依赖不存在 ID — 无检测无提示

**位置**: goal_helpers.py `_get_next_pending_subtask`

**问题**: 如果子任务 A 依赖 B，B 依赖 A（循环），或依赖 ID=99（不存在），`all(d in done_ids)` 永远为 False → 任务永远 pending → 最终 max_iterations 超限 → failed，但用户不知道为什么。

**影响**: 浪费 token + 用户体验差。

**修复**:
```python
def _validate_dependencies(goal_subtasks: list) -> list[str]:
    """校验依赖关系，返回问题列表"""
    issues = []
    ids = {t["id"] for t in goal_subtasks}
    for t in goal_subtasks:
        for dep in t.get("dependencies", []):
            if dep not in ids:
                issues.append(f"任务{t['id']}依赖不存在的任务{dep}")
    # 检测循环（拓扑排序）
    visited = set()
    in_stack = set()
    def has_cycle(task_id):
        if task_id in in_stack:
            return True
        if task_id in visited:
            return False
        visited.add(task_id)
        in_stack.add(task_id)
        for t in goal_subtasks:
            if t["id"] == task_id:
                for dep in t.get("dependencies", []):
                    if has_cycle(dep):
                        return True
        in_stack.discard(task_id)
        return False
    for t in goal_subtasks:
        if has_cycle(t["id"]):
            issues.append(f"检测到循环依赖（涉及任务{t['id']}）")
            break
    return issues
```

---

### 🟡 P4: 重复子任务 ID — _update_subtask_status 只更新第一个

**位置**: goal_helpers.py `_update_subtask_status`

**问题**: 如果 LLM 生成了两个 id=1 的子任务，`_update_subtask_status` 用列表推导式，会同时更新所有匹配的 id。但 `_get_next_pending_subtask` 会返回第一个匹配的，导致第二个被忽略。

**影响**: 子任务状态不一致。

**修复**: 在规划阶段校验 ID 唯一性。

---

### 🟡 P5: goal_history 无限膨胀

**位置**: goal_nodes.py `goal_replanner_node`

**问题**: `goal_history` 每轮追加，没有上限。5 轮迭代 × 每轮 200 字 ≈ 1000 字。如果 max_iterations 调大，history 可能很大。

**影响**: prompt 膨胀 → token 浪费。

**修复**:
```python
# 保留最近 N 条
MAX_HISTORY = 10
goal_history = list(state.get("goal_history") or [])[-MAX_HISTORY:]
```

---

### 🟡 P6: Working Memory 无上限

**位置**: state `goal_working_memory`

**问题**: 每个子任务完成都追加 result_summary（200字），8 个子任务 = 1600 字。如果重规划多次，working_memory 会累积更多。

**影响**: prompt 膨胀。

**修复**:
```python
# 保留最近 N 条，或按总字数截断
MAX_WM_ENTRIES = 15
goal_working_memory = list(state.get("goal_working_memory") or [])[-MAX_WM_ENTRIES:]
```

---

### 🟡 P7: 重规划后依赖 ID 重映射可能错误

**位置**: goal_nodes.py `goal_replanner_node`

**问题**: 
```python
"dependencies": [
    max_id + d if 1 <= d <= len(replan_result.subtasks) else d
    for d in st.dependencies
]
```
如果重规划结果的依赖引用了已完成任务的原始 ID（如 id=1），但 1 <= 1 <= len(subtasks) 为 True，会被错误地加上 max_id 偏移。

**影响**: 依赖关系错误 → 任务执行顺序错乱。

**修复**: 需要明确区分「重规划内部依赖」和「已完成任务依赖」。可以让 LLM 在重规划时只引用重规划内部的相对 ID。

---

### 🟢 P8: Goal 模式评估 prompt 与普通模式不一致

**位置**: nodes.py `evaluator_node`

**问题**: Goal 模式的 eval_prompt 是简化版（只有 score/passed/reason/suggestion），普通模式有 5 个维度。评分标准可能不一致。

**影响**: Goal 模式评估可能比普通模式更宽松或更严格。

---

### 🟢 P9: 无 streaming 进度反馈

**问题**: Goal 模式多轮迭代，用户看不到中间进度。虽然 writer 事件有 step/status，但没有实时推送到前端。

**影响**: 用户体验差，不知道 Agent 在做什么。

---

### 🟢 P10: token_budget 检查在 replanner，不在 llm_call

**位置**: goal_nodes.py `goal_replanner_node`

**问题**: token 预算检查只在 replanner 中做。如果单次 LLM 调用消耗大量 token，要到下一轮 replanner 才能发现超限。

**影响**: 可能超预算 1 轮。

---

## 四、进化方向（按优先级排序）

### Phase 1: 稳定性（P0-P2）— 立即修复

| # | 问题 | 修复方案 | 复杂度 |
|---|------|----------|--------|
| P0 | tool_choice 硬编码 | try/except 降级 | 低 |
| P1 | LoopDetector 全局单例 | 按 conversation_id 隔离 | 低 |
| P2 | 语义校验缓存共享 | 按 LLM 实例 ID 缓存 | 低 |
| P3 | 循环依赖无检测 | 规划后校验依赖关系 | 中 |
| P4 | 重复 ID | 规划后校验唯一性 | 低 |

### Phase 2: 健壮性（P3-P7）— 迭代优化

| # | 问题 | 修复方案 | 复杂度 |
|---|------|----------|--------|
| P5 | history 膨胀 | 保留最近 N 条 | 低 |
| P6 | working_memory 无上限 | 截断 | 低 |
| P7 | 依赖重映射错误 | 规范化重规划 ID 生成 | 中 |
| P8 | 评估 prompt 不一致 | 统一评估标准 | 低 |

### Phase 3: 体验增强 — 后续迭代

| # | 方向 | 说明 |
|---|------|------|
| P9 | Streaming 进度 | SSE 实时推送子任务状态 |
| P10 | Token 预算前置检查 | llm_call 中检查 |
| — | 并行子任务执行 | 当前只处理 1 个 in_progress，可并行多个 |
| — | 子任务超时控制 | 单个子任务执行时间限制 |
| — | 重规划次数限制 | 防止无限重规划 |
| — | 用户干预点 | 允许用户在子任务间介入调整计划 |

---

## 五、关键数据流验证

### 5.1 State 字段流转

```
goal_mode: InputState → llm_call(规划) → evaluator → memory_saver → status_updater → replanner
goal_iterations: llm_call(规划) → evaluator → replanner(递增) → llm_call(执行)
goal_subtasks: llm_call(规划) → status_updater(更新) → replanner(重规划) → llm_call(展示)
goal_status: replanner → _after_goal_replan → _after_memory → END
goal_working_memory: status_updater(累积) → replanner(读取) → llm_call(注入prompt)
evaluation: evaluator → status_updater(读取反馈)
current_tools_used: tool_executor → status_updater(记录到WM)
```

### 5.2 关键 Reducer 行为

```
messages: operator.add → 追加（每轮累积）
tools_used: operator.add → 追加（全量历史）
current_tools_used: 无 reducer → 覆盖（每轮独立）
goal_subtasks: 无 reducer → 覆盖（replanner 整体替换）
goal_working_memory: 无 reducer → 覆盖（status_updater 整体替换）
goal_history: 无 reducer → 覆盖（replanner 整体替换）
```

### 5.3 潜在死循环路径

```
路径1: llm_call → evaluator(passed) → memory_saver(skip) → status_updater(no current) → replanner(in_progress) → model_selector → llm_call → ...
  条件: 无 in_progress 且无 pending+deps满足 且 done<total
  结果: replanner 返回 failed → END ✅ 不会死循环

路径2: llm_call → evaluator(passed) → memory_saver(skip) → status_updater(retry) → replanner(in_progress) → model_selector → llm_call → ...
  条件: evaluator failed + retry_count<2
  结果: 最多重试 2 次 → failed 或 done ✅ 不会死循环

路径3: llm_call → evaluator(passed) → memory_saver(skip) → status_updater(done) → replanner(all done) → achieved → memory_saver(save) → END
  条件: 正常完成
  结果: ✅ 正确终止
```
