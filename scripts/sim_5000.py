#!/usr/bin/env python3
"""三模式 × 三任务 5000次模拟 — 正确率/幻觉率/子任务统计

前沿数据校准 (2025-2026 最新):
  - AgentDebug (ICML 2025): 级联失败是#1问题，定向反馈+26%
  - Reflexion (NeurIPS 2023): GSM8K 79→91%, HumanEval 71→85%
  - Self-Consistency (Wang 2023): GSM8K +17.9%, 3-5路径即可
  - LATS (Zhou 2023): 复杂推理 +20%, 成本 5-20x
  - FActScore (Min 2023): 原子声明级幻觉检测
  - NeurIPS 2025: 投票 > 辩论, 最佳=投票+辩论
  - DeepSeekMath-V2: Self-Consistency + Self-Refinement 组合最优

任务模型:
  - 长推理: 4步链, 上游失败→下游降权30%
  - 复杂目标: 5子任务, 依赖率60%, 级联传播
  - 超长子任务: 3阶段, 阶段间依赖

进化因子校准:
  - Reflexion: 每轮+12% 正确率 (GSM8K 79→91%, 约3轮)
  - Self-Consistency: +17.9% (3路径投票)
  - LATS/MCTS: +20% (树搜索10-25迭代)
  - Self-Correct: +9% (自评修正一次)
  - Reasoning: +6% (执行前反思)
  - Root Cause: +5% (5-Why根因)
  - Fact Verify: -12% 幻觉 (原子声明验证)
  - Grounding: -15% 幻觉 (知识引用)
  - Debate: -10% 幻觉 (交叉验证)
  - Cross-Goal: +4% (跨任务经验)
  - Rubric Eval: +4% (结构化评估)
  - Failure Isolation: 级联影响从30%降至12%
"""
import random
import math

random.seed(42)
N = 5000

# ── 进化因子 ──
EVOS = {
    "reasoning":       {"acc": +0.06, "hall": -0.02, "cost": 1.3},
    "tot":             {"acc": +0.08, "hall": -0.03, "cost": 2.5},
    "self_consistency":{"acc": +0.10, "hall": -0.04, "cost": 3.0},
    "reflexion":       {"acc": +0.12, "hall": -0.05, "cost": 1.5, "retry": 0.15},
    "debate":          {"acc": +0.04, "hall": -0.08, "cost": 2.0},
    "rubric_eval":     {"acc": +0.04, "hall": -0.03, "cost": 1.2},
    "self_correct":    {"acc": +0.07, "hall": -0.03, "cost": 1.3},
    "root_cause":      {"acc": +0.05, "hall": -0.02, "cost": 1.2},
    "fact_verify":     {"acc": +0.03, "hall": -0.12, "cost": 2.0},
    "grounding":       {"acc": +0.02, "hall": -0.15, "cost": 1.5},
    "lats_mcts":       {"acc": +0.15, "hall": -0.06, "cost": 8.0},
    "cross_goal":      {"acc": +0.04, "hall": -0.01, "cost": 1.1},
    "failure_isolation":{"acc": 0,    "hall": 0,      "cost": 1.1, "cascade_reduce": True},
}

def evo_bonus(evos):
    a, h, c = 0.0, 0.0, 1.0
    for i, e in enumerate(evos):
        if e in EVOS:
            d = 0.85 ** i
            a += EVOS[e]["acc"] * d
            h += abs(EVOS[e]["hall"]) * d
            c *= EVOS[e]["cost"]
    retry = any(EVOS.get(e, {}).get("retry") for e in evos if e in EVOS)
    cascade_reduce = any(EVOS.get(e, {}).get("cascade_reduce") for e in evos if e in EVOS)
    return {"acc": a, "hall": h, "cost": c, "retry": retry, "cascade_reduce": cascade_reduce}

def step(acc, hall, evo, mode):
    m_a = {"normal": 0, "expert": 0.04, "goal": 0.03}.get(mode, 0)
    m_h = {"normal": 0, "expert": -0.015, "goal": -0.01}.get(mode, 0)
    a = min(acc + m_a + evo["acc"], 0.995)
    h = max(hall + m_h - evo["hall"], 0.002)
    ok = random.random() < a
    hal = (not ok) and (random.random() < h)
    # Reflexion 重试
    if not ok and evo.get("retry"):
        if random.random() < 0.15:
            ok = True
            hal = False
    return ok, hal

# ═══════════════════════════════════════════
#  任务模拟
# ═══════════════════════════════════════════

def sim_long(cfg_mode, evo, chain_steps=4):
    """长推理: 4步链, 每步正确率递减, 上游失败→下游降权"""
    cascade = 0.12 if evo.get("cascade_reduce") else 0.30
    s_ok, s_hall, all_ok, prev_ok = 0, 0, True, True
    for i in range(chain_steps):
        ba = 0.88 - i * 0.04
        bh = 0.04 + i * 0.02
        if not prev_ok:
            ba *= (1 - cascade)
        ok, hal = step(ba, bh, evo, cfg_mode)
        if ok: s_ok += 1
        else: all_ok = False
        if hal: s_hall += 1
        prev_ok = ok
    return all_ok, s_hall > 0, s_ok, chain_steps, s_hall

def sim_complex(cfg_mode, evo, n_sub=5):
    """复杂目标: 5子任务, 依赖率60%, 级联传播"""
    cascade = 0.12 if evo.get("cascade_reduce") else 0.30
    results, done = [], set()
    for i in range(n_sub):
        ba = 0.85 - i * 0.03
        bh = 0.05 + i * 0.01
        if i > 0 and random.random() < 0.6 and done:
            dep = random.choice(list(done))
            if not results[dep][0]:
                ba *= (1 - cascade)
        ok, hal = step(ba, bh, evo, cfg_mode)
        results.append((ok, hal))
        if ok: done.add(i)
    all_ok = all(r[0] for r in results)
    total_hall = sum(1 for r in results if r[1])
    return all_ok, total_hall > 0, sum(1 for r in results if r[0]), n_sub, total_hall

def sim_ultra(cfg_mode, evo, n_phases=3):
    """超长子任务: 3阶段, 阶段间依赖"""
    cascade = 0.12 if evo.get("cascade_reduce") else 0.30
    results, prev_ok = [], True
    for i in range(n_phases):
        ba = 0.82 - i * 0.06
        bh = 0.06 + i * 0.03
        if not prev_ok:
            ba *= (1 - cascade)
        ok, hal = step(ba, bh, evo, cfg_mode)
        results.append((ok, hal))
        prev_ok = ok
    all_ok = all(r[0] for r in results)
    total_hall = sum(1 for r in results if r[1])
    return all_ok, total_hall > 0, sum(1 for r in results if r[0]), n_phases, total_hall

# ═══════════════════════════════════════════
#  批量运行
# ═══════════════════════════════════════════

def run(name, mode, evos, sim_fn, **kw):
    evo = evo_bonus(evos)
    evo["_evos"] = evos
    t_ok, t_hall, sub_ok, sub_total, sub_hall = 0, 0, 0, 0, 0
    for _ in range(N):
        ok, hall, so, st, sh = sim_fn(mode, evo, **kw)
        if ok: t_ok += 1
        if hall: t_hall += 1
        sub_ok += so; sub_total += st; sub_hall += sh
    return {
        "name": name, "task_acc": t_ok/N, "task_hall": t_hall/N,
        "sub_acc": sub_ok/sub_total, "sub_hall": sub_hall/sub_total,
        "cost": evo["cost"],
    }

def fmt(r, label="子任务"):
    return (f"  {r['name']:<35s} "
            f"任务正确 {r['task_acc']:>6.1%} | 任务幻觉 {r['task_hall']:>5.1%} | "
            f"{label}正确 {r['sub_acc']:>6.1%} | {label}幻觉 {r['sub_hall']:>5.1%} | "
            f"成本 {r['cost']:>5.1f}x")

# ═══════════════════════════════════════════
#  配置
# ═══════════════════════════════════════════

configs_long = [
    ("基线-普通-长推理",     "normal", []),
    ("基线-专家团-长推理",   "expert", []),
    ("基线-Goal-长推理",    "goal",   []),
    ("P0-普通-长推理",      "normal", ["reasoning", "self_correct"]),
    ("P0-专家团-长推理",     "expert", ["reasoning", "tot", "root_cause"]),
    ("P0-Goal-长推理",     "goal",   ["reasoning", "reflexion", "root_cause"]),
    ("P1-普通-长推理",      "normal", ["reasoning", "self_correct", "rubric_eval", "grounding"]),
    ("P1-专家团-长推理",     "expert", ["reasoning", "tot", "self_consistency", "debate", "reflexion", "root_cause", "grounding"]),
    ("P1-Goal-长推理",     "goal",   ["reasoning", "tot", "reflexion", "root_cause", "rubric_eval", "cross_goal", "grounding"]),
    ("反思增强-Goal-长推理", "goal",   ["reasoning", "reflexion", "self_correct"]),
    ("P2-Goal-长推理",     "goal",   ["reasoning", "tot", "self_consistency", "reflexion", "root_cause", "rubric_eval", "cross_goal", "fact_verify", "grounding"]),
]

configs_complex = [
    ("基线-普通-复杂目标",     "normal", []),
    ("基线-专家团-复杂目标",   "expert", []),
    ("基线-Goal-复杂目标",    "goal",   []),
    ("P0-普通-复杂目标",      "normal", ["reasoning", "self_correct"]),
    ("P0-专家团-复杂目标",     "expert", ["reasoning", "tot", "root_cause"]),
    ("P0-Goal-复杂目标",     "goal",   ["reasoning", "reflexion", "root_cause"]),
    ("P1-Goal-复杂目标",     "goal",   ["reasoning", "tot", "reflexion", "root_cause", "rubric_eval", "cross_goal", "grounding"]),
    ("反思增强-Goal-复杂目标", "goal",   ["reasoning", "reflexion", "self_correct"]),
    ("P2-Goal-复杂目标",     "goal",   ["reasoning", "tot", "self_consistency", "reflexion", "root_cause", "rubric_eval", "cross_goal", "fact_verify", "grounding"]),
]

configs_ultra = [
    ("基线-普通-超长子任务",     "normal", []),
    ("基线-专家团-超长子任务",   "expert", []),
    ("基线-Goal-超长子任务",    "goal",   []),
    ("P0-普通-超长子任务",      "normal", ["reasoning", "self_correct"]),
    ("P0-专家团-超长子任务",     "expert", ["reasoning", "tot", "root_cause"]),
    ("P0-Goal-超长子任务",     "goal",   ["reasoning", "reflexion", "root_cause"]),
    ("P1-Goal-超长子任务",     "goal",   ["reasoning", "tot", "reflexion", "root_cause", "rubric_eval", "cross_goal", "grounding"]),
    ("反思增强-Goal-超长子任务", "goal",   ["reasoning", "reflexion", "self_correct"]),
    ("P2-Goal-超长子任务",     "goal",   ["reasoning", "tot", "self_consistency", "reflexion", "root_cause", "rubric_eval", "cross_goal", "fact_verify", "grounding"]),
]

# ═══════════════════════════════════════════
#  执行
# ═══════════════════════════════════════════

print("=" * 110)
print(f"  三模式 × 三任务  {N}次/配置  模拟推理")
print("=" * 110)

for task_name, configs, sim_fn, label in [
    ("长推理任务 (4步链式推理)", configs_long, sim_long, "步骤"),
    ("复杂目标任务 (5子任务协同)", configs_complex, sim_complex, "子任务"),
    ("超长子任务 (3阶段递进)", configs_ultra, sim_ultra, "阶段"),
]:
    print(f"\n{'─' * 110}")
    print(f"  {task_name}")
    print(f"{'─' * 110}")
    for name, mode, evos in configs:
        r = run(name, mode, evos, sim_fn)
        print(fmt(r, label))

# ═══════════════════════════════════════════
#  进化因子贡献度
# ═══════════════════════════════════════════
print(f"\n{'=' * 110}")
print("  进化因子贡献度 (单独叠加到基线-Goal-长推理)")
print(f"{'=' * 110}")
print(f"  {'因子':<20s} {'任务正确↑':>10s} {'步骤正确↑':>10s} {'幻觉↓':>8s} {'成本':>8s} {'性价比':>8s}")
print(f"  {'─'*20} {'─'*10} {'─'*10} {'─'*8} {'─'*8} {'─'*8}")

bl = run("基线", "goal", [], sim_long)
for evo_name in EVOS:
    r = run(f"+{evo_name}", "goal", [evo_name], sim_long)
    ta = r["task_acc"] - bl["task_acc"]
    sa = r["sub_acc"] - bl["sub_acc"]
    sh = bl["sub_hall"] - r["sub_hall"]
    ci = max(r["cost"] - 1, 0.01)
    v = (ta + sa + sh) / ci
    print(f"  {evo_name:<20s} {ta:>+9.1%} {sa:>+9.1%} {sh:>+7.1%} {r['cost']:>7.1f}x {v:>7.1f}")

# ═══════════════════════════════════════════
#  最佳组合
# ═══════════════════════════════════════════
print(f"\n{'=' * 110}")
print("  最佳组合对比 (长推理)")
print(f"{'=' * 110}")

combos = [
    ("基础增强",    ["reasoning", "self_correct"]),
    ("反思增强",    ["reasoning", "reflexion", "self_correct"]),
    ("根因增强",    ["reasoning", "reflexion", "root_cause"]),
    ("多路径增强",   ["reasoning", "tot", "self_consistency"]),
    ("幻觉克星",    ["fact_verify", "grounding", "debate"]),
    ("全栈P1",     ["reasoning", "tot", "self_consistency", "reflexion", "root_cause", "rubric_eval", "grounding"]),
    ("全栈P2",     ["reasoning", "tot", "self_consistency", "reflexion", "root_cause", "rubric_eval", "fact_verify", "grounding", "cross_goal"]),
]

print(f"  {'组合':<12s} {'任务正确':>8s} {'步骤正确':>8s} {'步骤幻觉':>8s} {'成本':>8s} {'性价比':>8s}")
print(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
for name, evos in combos:
    r = run(name, "goal", evos, sim_long)
    ci = max(r["cost"] - 1, 0.01)
    v = (r["task_acc"] - bl["task_acc"] + bl["sub_hall"] - r["sub_hall"]) / ci
    print(f"  {name:<12s} {r['task_acc']:>7.1%} {r['sub_acc']:>7.1%} {r['sub_hall']:>7.1%} {r['cost']:>7.1f}x {v:>7.1f}")

# ═══════════════════════════════════════════
#  三任务 × 三模式 总览
# ═══════════════════════════════════════════
print(f"\n{'=' * 110}")
print("  三任务 × 反思增强 总览")
print(f"{'=' * 110}")
print(f"  {'任务':<20s} {'模式':<10s} {'任务正确':>8s} {'任务幻觉':>8s} {'子正确':>8s} {'子幻觉':>8s} {'成本':>6s}")
print(f"  {'─'*20} {'─'*10} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")
for tname, cfgs, sfn, lb in [
    ("长推理",     [("", "goal", ["reasoning", "reflexion", "self_correct"])], sim_long, "步骤"),
    ("复杂目标",    [("", "goal", ["reasoning", "reflexion", "self_correct"])], sim_complex, "子任务"),
    ("超长子任务",   [("", "goal", ["reasoning", "reflexion", "self_correct"])], sim_ultra, "阶段"),
]:
    for _, m, e in cfgs:
        r = run("", m, e, sfn)
        print(f"  {tname:<20s} {'反思增强':<10s} {r['task_acc']:>7.1%} {r['task_hall']:>7.1%} {r['sub_acc']:>7.1%} {r['sub_hall']:>7.1%} {r['cost']:>5.1f}x")

print(f"\n完成。")
