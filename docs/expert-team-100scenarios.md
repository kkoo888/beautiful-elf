# 专家团模式 100 场景推演 + 进化方向

> 审查时间: 2026-06-20
> 审查范围: expert_team_graph.py + expert_team_service.py + expert_team/* 全链路
> 方法: 逐条代码路径理论推断

---

## 一、完整流程图

```
用户输入
  ↓
┌─── PM Analyze ──────────────────────┐
│  PM 分析任务，输出分配计划 JSON      │
│  解析 assignments                    │
└──────────────────────────────────────┘
  ↓
┌─── Fan-out (Send API / asyncio.gather) ──────────────────────────┐
│  ┌─ Expert 1 ─┐  ┌─ Expert 2 ─┐  ┌─ Expert 3 ─┐               │
│  │ Reasoning   │  │ Reasoning   │  │ Reasoning   │               │
│  │ ToT         │  │ ToT         │  │ ToT         │               │
│  │ Planning    │  │ Planning    │  │ Planning    │               │
│  │ Knowledge   │  │ Knowledge   │  │ Knowledge   │               │
│  │ Memory      │  │ Memory      │  │ Memory      │               │
│  │ Self-Const  │  │ Self-Const  │  │ Self-Const  │               │
│  │ Execute     │  │ Execute     │  │ Execute     │               │
│  │ Guardrail   │  │ Guardrail   │  │ Guardrail   │               │
│  │ Delegation? │  │ Delegation? │  │ Delegation? │               │
│  │ Reflexion   │  │ Reflexion   │  │ Reflexion   │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
└───────────────────────────────────────────────────────────────────┘
  ↓
┌─── Multi-Agent Debate ─────────────┐
│  专家交叉审阅 → 共识度 < 0.7 修正   │
└──────────────────────────────────────┘
  ↓
┌─── PM Evaluate ────────────────────┐
│  评估打分 → overall_pass?          │
└──────────────────────────────────────┘
  ↓
  ┌── pass ──┐    ┌── fail ──────────┐
  │ PM Report│    │ feedback_map     │
  │ → END    │    │ round + 1        │
  └──────────┘    │ → PM Analyze     │
                  │ (max_rounds 限制) │
                  └──────────────────┘
```

---

## 二、100 场景推演

### A. PM 分析阶段 — 15 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 1 | PM 输出标准 JSON | _parse_assignments → 正常解析 | ✅ | OK |
| 2 | PM 输出 markdown code block | 正则提取 → 解析 | ✅ | OK |
| 3 | PM 输出非标准 JSON | 降级正则匹配 | ✅ | OK |
| 4 | PM 输出完全无法解析 | fallback: 全员分配 | ⚠️ 体验差 | **P3** |
| 5 | PM 返回空字符串 | fallback: 全员分配 | ⚠️ 浪费 token | **P3** |
| 6 | assignments 为空列表 | fallback: 全员分配 | ✅ | OK |
| 7 | expert_id 不存在 | expert_execute → "专家配置不存在" | ✅ 错误消息 | OK |
| 8 | PM LLM 超时 | asyncio.wait_for → TimeoutError | ❌ **未捕获** | **P0** |
| 9 | PM LLM 调用异常 | 直接抛出 → 外层 except | ✅ | OK |
| 10 | PM 输出多个 JSON 对象 | 只取第一个 | ⚠️ 可能取错 | **P3** |
| 11 | PM 分配了 0 个专家 | passthrough_evaluate → pm_evaluate | ✅ | OK |
| 12 | PM 分配了所有专家 | 全部 fan-out | ✅ | OK |
| 13 | PM 重复分配同一专家 | 同一 expert_id 多次 | ⚠️ 重复执行 | **P3** |
| 14 | orchestrator_prompt 为空 | 使用默认 prompt | ✅ | OK |
| 15 | leader_data 缺失 | RecordNotFoundError | ✅ | OK |

### B. 专家执行阶段 — 25 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 16 | 专家正常执行完成 | _call_llm → content, tokens | ✅ | OK |
| 17 | 专家执行超时 | asyncio.TimeoutError → failed | ✅ | OK |
| 18 | 专家执行异常 | Exception → failed | ✅ | OK |
| 19 | 专家输出为空 | guardrail: "输出过短" → retry | ✅ | OK |
| 20 | 专家输出包含幻觉 | guardrail: semantic check → retry | ✅ | OK |
| 21 | Guardrail 通过 | → 正常返回 | ✅ | OK |
| 22 | Guardrail 未通过 + 重试通过 | retry_with_feedback → 通过 | ✅ | OK |
| 23 | Guardrail 未通过 + 重试仍失败 | 返回重试后的结果（可能仍差） | ⚠️ 无最终兜底 | **P3** |
| 24 | 专家请求委派 | DELEGATE: id \| subtask | ✅ | OK |
| 25 | 委派目标不存在 | target_member=None → 忽略 | ⚠️ 静默失败 | **P3** |
| 26 | 委派目标也请求委派 | _delegation_depth >= 1 → 阻止 | ✅ 不递归 | OK |
| 27 | 委派执行失败 | delegate_result 输出失败消息 | ⚠️ 无重试 | **P3** |
| 28 | 委派执行超时 | 同专家超时处理 | ✅ | OK |
| 29 | Self-Consistency 3 路径全成功 | 投票选最佳 | ✅ | OK |
| 30 | Self-Consistency 部分路径失败 | 降级为单路径 | ✅ | OK |
| 31 | Self-Consistency 全部失败 | 返回错误 | ⚠️ 无降级 | **P2** |
| 32 | Self-Consistency 仅 round 1 | round 2+ 不启用 | ✅ 节省 token | OK |
| 33 | 知识源注入成功 | knowledge_text 注入 prompt | ✅ | OK |
| 34 | 知识源注入失败 | except → 跳过 | ✅ | OK |
| 35 | 记忆召回成功 | memory_text 注入 prompt | ✅ | OK |
| 36 | 记忆召回失败 | except → 跳过 | ✅ | OK |
| 37 | 专家无技能绑定 | skill_text="" | ✅ | OK |
| 38 | 专家有技能 + 工具 | 临时注册工具 → 执行 → 清理 | ✅ | OK |
| 39 | 临时工具注册名冲突 | 覆盖已有工具 | ⚠️ 并发风险 | **P1** |
| 40 | 工具清理 finally | _tools.pop(tid) | ⚠️ 可能误删 | **P2** |

### C. PM 评估阶段 — 15 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 41 | PM 评估 JSON 正常 | _parse_evaluation → overall_pass | ✅ | OK |
| 42 | PM 评估 JSON 在 code block | 正则提取 | ✅ | OK |
| 43 | PM 评估完全无法解析 | 关键词降级: "达标"/"pass" | ⚠️ 可能误判 | **P2** |
| 44 | PM 评估超时 | asyncio.wait_for → 120s | ❌ **未单独捕获** | **P0** |
| 45 | PM 评估 LLM 异常 | 直接抛出 | ✅ 外层捕获 | OK |
| 46 | 评估 overall_pass=True | → pm_report | ✅ | OK |
| 47 | 评估 overall_pass=False | → feedback_map → 下一轮 | ✅ | OK |
| 48 | 评估 feedback_map 为空 | 下轮无反馈注入 | ⚠️ 无效返工 | **P3** |
| 49 | 评估 score 缺失 expert_id | feedback_map 跳过 | ✅ | OK |
| 50 | 评估 score 缺失 feedback | feedback_map 跳过 | ✅ | OK |

### D. 循环控制 — 15 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 51 | 第 1 轮通过 | break → pm_report | ✅ | OK |
| 52 | 第 2 轮通过 | break → pm_report | ✅ | OK |
| 53 | 第 3 轮未通过 + max_rounds=3 | current_round >= max → pm_report | ✅ 强制结束 | OK |
| 54 | max_rounds=1 | 只执行一轮 | ✅ | OK |
| 55 | max_rounds=10 | 最多 10 轮 | ✅ | OK |
| 56 | max_rounds=0 | 不执行？ | ⚠️ 可能异常 | **P3** |
| 57 | 所有专家失败 + PM 评估 | PM 看到全是失败输出 | ⚠️ 可能误判 pass | **P2** |
| 58 | 部分专家失败 + PM 评估 | PM 看到混合结果 | ✅ | OK |
| 59 | 每轮 token 累加 | total_tokens += round | ✅ | OK |
| 60 | 无 token 预算限制 | total_tokens 只累加不检查 | ⚠️ 可能失控 | **P2** |

### E. 辩论机制 — 10 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 61 | 2+ 专家 → 辩论启动 | run_debate_round | ✅ | OK |
| 62 | 共识度 >= 0.7 | 不修正 | ✅ | OK |
| 63 | 共识度 < 0.7 | revise_opinion → 修正输出 | ✅ | OK |
| 64 | 辩论 LLM 超时 | except → 降级无辩论 | ✅ | OK |
| 65 | 辩论 LLM 异常 | except → 降级 | ✅ | OK |
| 66 | 只有 1 个专家 | len < 2 → 跳过辩论 | ✅ | OK |
| 67 | 辩论修正后输出更差 | 无回滚机制 | ⚠️ 无保护 | **P3** |
| 68 | revise_opinion 返回空 | 保持原输出 | ✅ | OK |
| 69 | 辩论 + 评估交互 | 修正后的输出 → PM 评估 | ✅ | OK |
| 70 | 辩论结果存入 discussion | discussion.append | ✅ | OK |

### F. 记忆 & 经验 — 10 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 71 | Reflexion 成功 | generate_reflexion → store | ✅ | OK |
| 72 | Reflexion 失败 | except → 跳过 | ✅ | OK |
| 73 | 事实提取成功 | extract_facts → store | ✅ | OK |
| 74 | 事实提取失败 | except → 跳过 | ✅ | OK |
| 75 | 经验存储成功 | store_experience | ✅ | OK |
| 76 | 经验存储失败 | except → 跳过 | ✅ | OK |
| 77 | 记忆召回有结果 | memory_text 注入 | ✅ | OK |
| 78 | 记忆召回无结果 | memory_text="" | ✅ | OK |
| 79 | 知识源有绑定 | knowledge_text 注入 | ✅ | OK |
| 80 | 知识源无绑定 | knowledge_text="" | ✅ | OK |

### G. 检查点 & 恢复 — 5 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 81 | PM 计划完成 → 保存 | save_checkpoint(PM_PLAN) | ✅ | OK |
| 82 | 专家完成 → 保存 | save_checkpoint(EXPERT_DONE) | ✅ | OK |
| 83 | 检查点保存失败 | except → 跳过 | ✅ 非致命 | OK |
| 84 | 从检查点恢复 | resume_from_checkpoint | ✅ | OK |
| 85 | 检查点数据损坏 | load 失败 | ⚠️ 无降级 | **P3** |

### H. WebSocket 事件 — 10 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 86 | expert_start 事件 | _ws_broadcast | ✅ | OK |
| 87 | expert_thinking 事件 | _ws_broadcast | ✅ | OK |
| 88 | expert_done 事件 | _ws_broadcast | ✅ | OK |
| 89 | expert_status 事件 | _ws_broadcast | ✅ | OK |
| 90 | pm_plan 事件 | _ws_broadcast | ✅ | OK |
| 91 | pm_eval 事件 | _ws_broadcast | ✅ | OK |
| 92 | pm_report 事件 | _ws_broadcast | ✅ | OK |
| 93 | expert_progress(completed) | _ws_broadcast | ✅ | OK |
| 94 | WebSocket 连接断开 | _ws_broadcast 异常 | ⚠️ 未处理 | **P3** |
| 95 | 并发 expert_start 事件 | 多个专家同时推送 | ✅ 独立 | OK |

### I. 资源 & 并发 — 5 场景

| # | 场景 | 代码路径 | 结果 | 状态 |
|---|------|----------|------|------|
| 96 | 3 个专家并行 | asyncio.gather | ✅ | OK |
| 97 | 10 个专家并行 | asyncio.gather | ⚠️ LLM 并发压力 | **P2** |
| 98 | 顺序模式 | process_mode=sequential | ✅ | OK |
| 99 | 工具注册表并发写入 | _tools[tid] = ... | ⚠️ 竞态条件 | **P1** |
| 100 | 工具清理误删 | finally: _tools.pop | ⚠️ 可能删错 | **P2** |

---

## 三、发现的问题汇总

### 🔴 P0: PM 分析/评估超时未单独捕获

**位置**: expert_team_service.py `_call_llm` + `asyncio.wait_for`

**问题**: PM 分析用 `asyncio.wait_for(..., timeout=120)` 但外层没有单独捕获 `TimeoutError`。如果 PM 超时，整个专家团执行失败，无降级。

**影响**: PM 是单点故障，超时 = 全部失败。

**修复**:
```python
try:
    plan_content, plan_tokens = await asyncio.wait_for(...)
except asyncio.TimeoutError:
    # 降级：全员分配原始任务
    assignments = [{"expert_id": e["id"], "subtask": request.input_text} for e in experts_data]
```

---

### 🔴 P1: 工具注册表并发竞态条件

**位置**: expert_team_service.py `_run_one_expert`

**问题**: 多个专家并行执行时，都可能临时注册工具到 `tool_registry._tools`。如果两个专家注册同名工具，后注册的会覆盖先注册的。执行完后 `finally: _tools.pop` 可能删掉对方的工具。

**影响**: 并发场景下工具丢失或错乱。

**修复**:
```python
# 方案1: 每个专家用自己的工具快照（推荐）
expert_tools = {**tool_registry._tools}  # 快照
for s in skills:
    expert_tools[tool_name] = ToolDef(...)
# 用 expert_tools 执行，不污染全局

# 方案2: 加锁
async with tool_registry._lock:
    tool_registry._tools[tool_name] = ...
```

---

### 🟡 P2: PM 评估关键词降级可能误判

**位置**: expert_team_service.py `_parse_evaluation`

**问题**: 当 JSON 解析全部失败时，降级为关键词匹配：
```python
passed = '"overall_pass": true' in lower or '达标' in eval_output or '"pass"' in lower
```
如果 PM 说「这个方案不达标」，会匹配到「达标」→ 误判为 pass。

**影响**: 不合格的专家结果被放行。

**修复**:
```python
# 更精确的关键词匹配
passed = ('"overall_pass": true' in lower 
          or ('达标' in eval_output and '不达标' not in eval_output)
          or '"pass": true' in lower)
```

---

### 🟡 P3: 工具清理可能误删

**位置**: expert_team_service.py `finally: tool_registry._tools.pop(tid, None)`

**问题**: 如果专家 A 注册了工具 X，专家 B（并行）也注册了同名工具 X，专家 A 完成后 `pop("X")` 会删掉专家 B 正在用的工具。

**影响**: 与 P1 同源，并发场景下工具丢失。

**修复**: 同 P1，用工具快照隔离。

---

### 🟡 P4: 无 Token 预算限制

**位置**: expert_team_service.py `execute_team`

**问题**: `total_tokens` 只累加不检查。如果专家团有 5 个专家 × 3 轮 × Self-Consistency 3 路径 = 45 次 LLM 调用，token 消耗可能非常大。

**影响**: 成本失控。

**修复**:
```python
MAX_TOTAL_TOKENS = 200000
if total_tokens > MAX_TOTAL_TOKENS:
    logger.warning(f"Token 预算超限: {total_tokens}")
    break  # 强制结束循环
```

---

### 🟡 P5: Self-Consistency 全部失败无降级

**位置**: expert_team/consistency.py

**问题**: 如果 3 条路径全部失败，`execute_with_self_consistency` 可能返回错误而非降级到单路径。

**影响**: 专家执行直接失败。

**修复**: 在 consistency.py 中确保全失败时降级为单路径执行。

---

### 🟡 P6: 上下文无限膨胀

**位置**: expert_team_service.py 循环构建 `context_text`

**问题**: 每轮都把之前所有轮次的完整输出拼入 context。3 轮 × 5 专家 × 每个 2000 字 = 30000 字 context。

**影响**: prompt 超长 → LLM 截断 → 质量下降。

**修复**:
```python
# 只保留最近 1 轮的上下文
recent_results = [r for r in all_round_results if r.get("round", 0) >= round_num - 1]
```

---

### 🟢 P7: 委派失败无重试

**位置**: expert_team_service.py 委派处理

**问题**: 委派的专家执行失败后，直接把失败消息拼入原专家输出，没有重试。

**影响**: 委派质量无保障。

---

### 🟢 P8: max_rounds=0 未校验

**位置**: expert_team_service.py

**问题**: 如果 `max_rounds=0`，`range(1, 0+1)` = `range(1, 1)` = 空，不执行任何专家，直接跳到报告。

**影响**: 无专家执行，报告无内容。

---

### 🟢 P9: 辩论修正后输出可能更差

**位置**: expert_team_service.py 辩论修正

**问题**: `revise_opinion` 修正后的输出可能比原版更差，但没有回滚机制。

**影响**: 辩论反而降低质量。

---

### 🟢 P10: WebSocket 事件未做异常隔离

**位置**: expert_team_graph.py + expert_team_service.py

**问题**: `_ws_broadcast` 如果抛异常，可能中断主流程。

**影响**: 推送失败导致执行中断。

**修复**: 所有 `_ws_broadcast` 调用都包在 try/except 中（部分已做，部分未做）。

---

## 四、进化方向

### Phase 1: 稳定性（P0-P3）— 立即修复

| # | 问题 | 修复方案 | 复杂度 |
|---|------|----------|--------|
| P0 | PM 超时未捕获 | try/except TimeoutError → 降级全员分配 | 低 |
| P1 | 工具注册表并发竞态 | 专家级工具快照隔离 | 中 |
| P2 | PM 评估关键词误判 | 排除「不达标」等否定词 | 低 |
| P3 | 工具清理误删 | 同 P1 | 中 |

### Phase 2: 健壮性（P4-P6）— 迭代优化

| # | 问题 | 修复方案 | 复杂度 |
|---|------|----------|--------|
| P4 | 无 Token 预算 | 添加 MAX_TOTAL_TOKENS 检查 | 低 |
| P5 | Self-Consistency 全失败 | 降级为单路径 | 低 |
| P6 | 上下文膨胀 | 只保留最近 1 轮 | 低 |

### Phase 3: 体验增强 — 后续迭代

| # | 方向 | 说明 |
|---|------|------|
| — | 流式专家输出 | SSE 实时推送每个专家的思考过程 |
| — | 专家动态调度 | 根据任务复杂度自动选择专家数量 |
| — | 成本预估 | 执行前预估 token 消耗，超限提醒 |
| — | 专家技能自动匹配 | 根据子任务内容自动选择最合适的技能 |
| — | 人类介入点 | 允许用户在 PM 评估前介入调整 |
| — | 专家结果缓存 | 相同子任务不重复执行 |

---

## 五、关键数据流验证

### 5.1 State 字段流转

```
input_text: 传入 → pm_analyze(读) → expert_execute(读) → pm_evaluate(读) → pm_report(读)
assignments: pm_analyze(写) → fan_out_experts(读) → expert_execute(读)
expert_results: expert_execute(写, reducer) → pm_evaluate(读) → pm_report(读)
pm_evaluation: pm_evaluate(写) → route_after_evaluate(读)
feedback_map: pm_evaluate(写) → pm_analyze(读, 下轮)
current_round: increment_round(递增) → pm_analyze(读) → expert_execute(读)
discussion: 每个节点追加 → pm_report(读, 汇总)
```

### 5.2 潜在死循环路径

```
路径: pm_analyze → expert_execute → pm_evaluate(fail) → increment_round → pm_analyze → ...
保护: max_rounds 限制 ✅
风险: max_rounds=0 或 current_round 未正确递增 → 无风险（range(1, max+1) 已保护）
```

### 5.3 并发安全分析

```
expert_execute: Send API 并发 → expert_results reducer(_merge_dicts) → 安全 ✅
tool_registry: _tools dict 并发写入 → 不安全 ❌ (P1)
ws_broadcast: 独立连接 → 安全 ✅
discussion: list.append → GIL 保护 → 安全 ✅
total_tokens: 单线程累加（串行循环）→ 安全 ✅
```
