#!/usr/bin/env python3
"""长推理/复杂目标/超长子任务 2000次模拟器

任务类型:
  1. 长推理任务: 多步推理链,每步依赖上一步,如"分析→推理→验证→结论"
  2. 复杂目标任务: 需拆解为多个子任务协同完成,如"写一份完整的技术方案"
  3. 超长子任务: 单个子任务本身就很复杂,如"分析1000行代码的架构问题"

模拟方法: 链式依赖模型 — 每步正确率乘积决定最终正确率
  - 长推理: 4步链,每步独立正确率
  - 复杂目标: 5个子任务,子任务间有依赖
  - 超长子任务: 1个任务但内部分3个阶段

前沿数据校准:
  - Reflexion: 每轮迭代 +12% 正确率 (HumanEval 67→91%, 3轮)
  - Self-Consistency: +17.9% (GSM8K 56.5→74.4%)
  - LATS/MCTS: 复杂推理 +20% (树搜索)
  - Fact Verify: 幻觉率 -12% (原子声明验证)
  - Grounding: 幻觉率 -15% (知识引用)
  - 辩论: 幻觉率 -10% (交叉验证)
  - 子任务依赖失败传播: 上游失败导致下游成功率降 30%
"""
import random
import math
from dataclasses import dataclass, field
from typing import List, Dict
from collections import Counter

random.seed(42)


# ═══════════════════════════════════════════════════════
#  任务模型
# ═══════════════════════════════════════════════════════

@dataclass
class TaskConfig:
    name: str
    mode: str           # normal / expert / goal
    n_runs: int = 2000
    evolutions: list = field(default_factory=list)
    # 子任务配置
    chain_steps: int = 4        # 长推理链步数
    subtask_count: int = 5      # 复杂目标子任务数
    phases_per_task: int = 3    # 超长子任务内部分阶段数
    # 依赖配置
    dependency_rate: float = 0.6  # 子任务间依赖概率
    failure_propagation: float = 0.3  # 上游失败对下游的影响


# ═══════════════════════════════════════════════════════
#  进化因子 (前沿论文数据校准)
# ═══════════════════════════════════════════════════════

EVOS = {
    # 每步/每子任务的提升
    "reasoning":       {"step_acc": +0.06, "hall": -0.02, "cost": 1.3},
    "tot":             {"step_acc": +0.08, "hall": -0.03, "cost": 2.5},
    "self_consistency":{"step_acc": +0.10, "hall": -0.04, "cost": 3.0},
    "reflexion":       {"step_acc": +0.12, "hall": -0.05, "cost": 1.5},
    "debate":          {"step_acc": +0.04, "hall": -0.08, "cost": 2.0},
    "rubric_eval":     {"step_acc": +0.04, "hall": -0.03, "cost": 1.2},
    "self_correct":    {"step_acc": +0.07, "hall": -0.03, "cost": 1.3},
    "root_cause":      {"step_acc": +0.05, "hall": -0.02, "cost": 1.2},
    "fact_verify":     {"step_acc": +0.03, "hall": -0.12, "cost": 2.0},
    "grounding":       {"step_acc": +0.02, "hall": -0.15, "cost": 1.5},
    "lats_mcts":       {"step_acc": +0.15, "hall": -0.06, "cost": 8.0},
    "cross_goal":      {"step_acc": +0.04, "hall": -0.01, "cost": 1.1},
}


def get_evo_bonus(evolutions: list) -> dict:
    """计算进化因子叠加 (边际递减 15%)"""
    acc_bonus = 0.0
    hall_bonus = 0.0
    cost = 1.0
    for i, evo in enumerate(evolutions):
        if evo in EVOS:
            decay = 0.85 ** i
            acc_bonus += EVOS[evo]["step_acc"] * decay
            hall_bonus += abs(EVOS[evo]["hall"]) * decay
            cost *= EVOS[evo]["cost"]
    return {"acc": acc_bonus, "hall": hall_bonus, "cost": cost}


# ═══════════════════════════════════════════════════════
#  模拟器
# ═══════════════════════════════════════════════════════

def sim_step(base_acc: float, base_hall: float, evo: dict, mode: str) -> dict:
    """模拟单步推理"""
    # 模式修正
    mode_acc = {"normal": 0, "expert": 0.04, "goal": 0.03}.get(mode, 0)
    mode_hall = {"normal": 0, "expert": -0.015, "goal": -0.01}.get(mode, 0)

    acc = min(base_acc + mode_acc + evo["acc"], 0.995)
    hall = max(base_hall + mode_hall - evo["hall"], 0.002)

    correct = random.random() < acc
    hallucinated = (not correct) and (random.random() < hall)

    # Reflexion 重试
    if not correct and "reflexion" in evo.get("_evos", []):
        if random.random() < 0.15:  # Reflexion 重试成功率
            correct = True

    return {"correct": correct, "hallucinated": hallucinated}


def sim_long_reasoning(cfg: TaskConfig, evo: dict) -> dict:
    """长推理任务: N步链式推理,每步依赖上一步

    链式正确率 = ∏(每步正确率)
    上游失败 → 下游正确率降 30%
    """
    steps_correct = 0
    steps_hallucinated = 0
    chain_correct = True
    prev_correct = True

    for step in range(cfg.chain_steps):
        # 基础正确率随步骤递减 (推理链越长越容易出错)
        base_acc = 0.88 - step * 0.04  # 0.88, 0.84, 0.80, 0.76
        base_hall = 0.04 + step * 0.02  # 0.04, 0.06, 0.08, 0.10

        # 上游失败传播
        if not prev_correct:
            base_acc *= (1 - cfg.failure_propagation)

        r = sim_step(base_acc, base_hall, evo, cfg.mode)
        if r["correct"]:
            steps_correct += 1
        else:
            chain_correct = False
        if r["hallucinated"]:
            steps_hallucinated += 1
        prev_correct = r["correct"]

    return {
        "task_correct": chain_correct,
        "task_hallucinated": steps_hallucinated > 0,
        "steps_correct": steps_correct,
        "steps_total": cfg.chain_steps,
        "steps_hallucinated": steps_hallucinated,
    }


def sim_complex_goal(cfg: TaskConfig, evo: dict) -> dict:
    """复杂目标任务: N个子任务,有依赖关系

    子任务正确率独立计算
    有依赖的子任务: 上游失败 → 自身正确率降 30%
    总任务正确 = 所有子任务都正确
    """
    subtask_results = []
    completed_ids = set()

    for i in range(cfg.subtask_count):
        # 子任务复杂度递增
        base_acc = 0.85 - i * 0.03  # 0.85, 0.82, 0.79, 0.76, 0.73
        base_hall = 0.05 + i * 0.01  # 0.05, 0.06, 0.07, 0.08, 0.09

        # 依赖检查
        has_dependency = i > 0 and random.random() < cfg.dependency_rate
        if has_dependency and i > 0:
            dep_id = random.choice(list(completed_ids)) if completed_ids else -1
            if dep_id >= 0 and dep_id < len(subtask_results):
                if not subtask_results[dep_id]["correct"]:
                    base_acc *= (1 - cfg.failure_propagation)

        r = sim_step(base_acc, base_hall, evo, cfg.mode)
        subtask_results.append(r)
        if r["correct"]:
            completed_ids.add(i)

    all_correct = all(r["correct"] for r in subtask_results)
    total_hall = sum(1 for r in subtask_results if r["hallucinated"])

    return {
        "task_correct": all_correct,
        "task_hallucinated": total_hall > 0,
        "subtasks_correct": sum(1 for r in subtask_results if r["correct"]),
        "subtasks_total": cfg.subtask_count,
        "subtasks_hallucinated": total_hall,
    }


def sim_ultra_long_subtask(cfg: TaskConfig, evo: dict) -> dict:
    """超长子任务: 单任务内部分N个阶段

    每阶段有独立正确率
    阶段间有依赖 (前阶段失败 → 后阶段降权)
    总任务正确 = 所有阶段都正确
    """
    phase_results = []
    prev_correct = True

    for phase in range(cfg.phases_per_task):
        # 阶段复杂度递增
        base_acc = 0.82 - phase * 0.06  # 0.82, 0.76, 0.70
        base_hall = 0.06 + phase * 0.03  # 0.06, 0.09, 0.12

        if not prev_correct:
            base_acc *= (1 - cfg.failure_propagation)

        r = sim_step(base_acc, base_hall, evo, cfg.mode)
        phase_results.append(r)
        prev_correct = r["correct"]

    all_correct = all(r["correct"] for r in phase_results)
    total_hall = sum(1 for r in phase_results if r["hallucinated"])

    return {
        "task_correct": all_correct,
        "task_hallucinated": total_hall > 0,
        "phases_correct": sum(1 for r in phase_results if r["correct"]),
        "phases_total": cfg.phases_per_task,
        "phases_hallucinated": total_hall,
    }


# ═══════════════════════════════════════════════════════
#  运行模拟
# ═══════════════════════════════════════════════════════

def run_batch(cfg: TaskConfig, sim_fn) -> dict:
    """批量运行模拟"""
    evo = get_evo_bonus(cfg.evolutions)
    evo["_evos"] = cfg.evolutions

    results = []
    for _ in range(cfg.n_runs):
        results.append(sim_fn(cfg, evo))

    task_correct = sum(1 for r in results if r["task_correct"])
    task_hall = sum(1 for r in results if r["task_hallucinated"])

    # 子任务/步骤统计
    if "steps_correct" in results[0]:
        total_steps = sum(r["steps_total"] for r in results)
        correct_steps = sum(r["steps_correct"] for r in results)
        hall_steps = sum(r["steps_hallucinated"] for r in results)
        sub_label = "步骤"
    elif "subtasks_correct" in results[0]:
        total_steps = sum(r["subtasks_total"] for r in results)
        correct_steps = sum(r["subtasks_correct"] for r in results)
        hall_steps = sum(r["subtasks_hallucinated"] for r in results)
        sub_label = "子任务"
    else:
        total_steps = sum(r["phases_total"] for r in results)
        correct_steps = sum(r["phases_correct"] for r in results)
        hall_steps = sum(r["phases_hallucinated"] for r in results)
        sub_label = "阶段"

    return {
        "name": cfg.name,
        "mode": cfg.mode,
        "task_type": sim_fn.__name__,
        "n": cfg.n_runs,
        "task_acc": task_correct / cfg.n_runs,
        "task_hall": task_hall / cfg.n_runs,
        f"{sub_label}_acc": correct_steps / total_steps,
        f"{sub_label}_hall": hall_steps / total_steps,
        "sub_label": sub_label,
        "cost": evo["cost"],
        "evolutions": cfg.evolutions,
    }


def fmt(r: dict) -> str:
    """格式化输出"""
    sl = r["sub_label"]
    return (
        f"  {r['name']:<32s} "
        f"任务正确 {r['task_acc']:>6.1%} | 任务幻觉 {r['task_hall']:>5.1%} | "
        f"{sl}正确 {r[f'{sl}_acc']:>6.1%} | {sl}幻觉 {r[f'{sl}_hall']:>5.1%} | "
        f"成本 {r['cost']:>5.1f}x"
    )


# ═══════════════════════════════════════════════════════
#  配置 & 执行
# ═══════════════════════════════════════════════════════

N = 2000

configs = [
    # ── 长推理任务 ──
    TaskConfig("基线-普通-长推理", "normal", N, chain_steps=4),
    TaskConfig("基线-专家团-长推理", "expert", N, chain_steps=4),
    TaskConfig("基线-Goal-长推理", "goal", N, chain_steps=4),
    TaskConfig("P0-普通-长推理", "normal", N, chain_steps=4,
               evolutions=["reasoning", "self_correct"]),
    TaskConfig("P0-专家团-长推理", "expert", N, chain_steps=4,
               evolutions=["reasoning", "tot", "root_cause"]),
    TaskConfig("P0-Goal-长推理", "goal", N, chain_steps=4,
               evolutions=["reasoning", "reflexion", "root_cause"]),
    TaskConfig("P1-普通-长推理", "normal", N, chain_steps=4,
               evolutions=["reasoning", "self_correct", "rubric_eval", "grounding"]),
    TaskConfig("P1-专家团-长推理", "expert", N, chain_steps=4,
               evolutions=["reasoning", "tot", "self_consistency", "debate",
                           "reflexion", "root_cause", "grounding"]),
    TaskConfig("P1-Goal-长推理", "goal", N, chain_steps=4,
               evolutions=["reasoning", "tot", "reflexion", "root_cause",
                           "rubric_eval", "cross_goal", "grounding"]),
    TaskConfig("P2-普通-长推理", "normal", N, chain_steps=4,
               evolutions=["reasoning", "tot", "self_consistency", "self_correct",
                           "rubric_eval", "fact_verify", "grounding"]),
    TaskConfig("P2-专家团-长推理", "expert", N, chain_steps=4,
               evolutions=["reasoning", "tot", "self_consistency", "debate",
                           "reflexion", "root_cause", "rubric_eval", "fact_verify",
                           "grounding", "cross_goal"]),
    TaskConfig("P2-Goal-长推理", "goal", N, chain_steps=4,
               evolutions=["reasoning", "tot", "self_consistency", "reflexion",
                           "root_cause", "rubric_eval", "cross_goal",
                           "fact_verify", "grounding"]),

    # ── 复杂目标任务 ──
    TaskConfig("基线-普通-复杂目标", "normal", N, subtask_count=5),
    TaskConfig("基线-专家团-复杂目标", "expert", N, subtask_count=5),
    TaskConfig("基线-Goal-复杂目标", "goal", N, subtask_count=5),
    TaskConfig("P0-普通-复杂目标", "normal", N, subtask_count=5,
               evolutions=["reasoning", "self_correct"]),
    TaskConfig("P0-专家团-复杂目标", "expert", N, subtask_count=5,
               evolutions=["reasoning", "tot", "root_cause"]),
    TaskConfig("P0-Goal-复杂目标", "goal", N, subtask_count=5,
               evolutions=["reasoning", "reflexion", "root_cause"]),
    TaskConfig("P1-Goal-复杂目标", "goal", N, subtask_count=5,
               evolutions=["reasoning", "tot", "reflexion", "root_cause",
                           "rubric_eval", "cross_goal", "grounding"]),
    TaskConfig("P2-Goal-复杂目标", "goal", N, subtask_count=5,
               evolutions=["reasoning", "tot", "self_consistency", "reflexion",
                           "root_cause", "rubric_eval", "cross_goal",
                           "fact_verify", "grounding"]),

    # ── 超长子任务 ──
    TaskConfig("基线-普通-超长子任务", "normal", N, phases_per_task=3),
    TaskConfig("基线-专家团-超长子任务", "expert", N, phases_per_task=3),
    TaskConfig("基线-Goal-超长子任务", "goal", N, phases_per_task=3),
    TaskConfig("P0-普通-超长子任务", "normal", N, phases_per_task=3,
               evolutions=["reasoning", "self_correct"]),
    TaskConfig("P0-专家团-超长子任务", "expert", N, phases_per_task=3,
               evolutions=["reasoning", "tot", "root_cause"]),
    TaskConfig("P0-Goal-超长子任务", "goal", N, phases_per_task=3,
               evolutions=["reasoning", "reflexion", "root_cause"]),
    TaskConfig("P1-Goal-超长子任务", "goal", N, phases_per_task=3,
               evolutions=["reasoning", "tot", "reflexion", "root_cause",
                           "rubric_eval", "cross_goal", "grounding"]),
    TaskConfig("P2-Goal-超长子任务", "goal", N, phases_per_task=3,
               evolutions=["reasoning", "tot", "self_consistency", "reflexion",
                           "root_cause", "rubric_eval", "cross_goal",
                           "fact_verify", "grounding"]),
]

sim_fns = {
    "长推理": sim_long_reasoning,
    "复杂目标": sim_complex_goal,
    "超长子任务": sim_ultra_long_subtask,
}

# 按任务类型分组
task_type_map = {}
for cfg in configs:
    if "长推理" in cfg.name:
        tt = "长推理"
    elif "复杂目标" in cfg.name:
        tt = "复杂目标"
    else:
        tt = "超长子任务"
    task_type_map.setdefault(tt, []).append(cfg)

print("=" * 100)
print("  长推理 / 复杂目标 / 超长子任务  2000次模拟推理")
print("=" * 100)

all_results = []
for task_type, cfgs in task_type_map.items():
    sim_fn = sim_fns[task_type]
    print(f"\n{'─' * 100}")
    print(f"  {task_type}任务")
    print(f"{'─' * 100}")
    for cfg in cfgs:
        r = run_batch(cfg, sim_fn)
        all_results.append(r)
        print(fmt(r))

# ═══════════════════════════════════════════════════════
#  进化因子贡献度
# ═══════════════════════════════════════════════════════
print(f"\n{'=' * 100}")
print("  进化因子贡献度 (单独叠加到基线-Goal-长推理)")
print(f"{'=' * 100}")
print(f"  {'因子':<20s} {'任务正确↑':>10s} {'步骤正确↑':>10s} {'幻觉↓':>8s} {'成本':>8s} {'性价比':>8s}")
print(f"  {'─'*20} {'─'*10} {'─'*10} {'─'*8} {'─'*8} {'─'*8}")

baseline_cfg = TaskConfig("基线", "goal", N, chain_steps=4)
baseline_r = run_batch(baseline_cfg, sim_long_reasoning)

for evo_name, evo_data in EVOS.items():
    cfg = TaskConfig(f"+{evo_name}", "goal", N, chain_steps=4, evolutions=[evo_name])
    r = run_batch(cfg, sim_long_reasoning)
    task_gain = r["task_acc"] - baseline_r["task_acc"]
    step_gain = r["步骤_acc"] - baseline_r["步骤_acc"]
    hall_gain = baseline_r["步骤_hall"] - r["步骤_hall"]
    cost_inc = max(r["cost"] - 1, 0.01)
    value = (task_gain + step_gain + hall_gain) / cost_inc
    print(f"  {evo_name:<20s} {task_gain:>+9.1%} {step_gain:>+9.1%} {hall_gain:>+7.1%} {r['cost']:>7.1f}x {value:>7.1f}")

# ═══════════════════════════════════════════════════════
#  最佳组合
# ═══════════════════════════════════════════════════════
print(f"\n{'=' * 100}")
print("  最佳组合 (长推理任务)")
print(f"{'=' * 100}")

combos = [
    ("基础增强", ["reasoning", "self_correct"]),
    ("反思增强", ["reasoning", "reflexion", "self_correct"]),
    ("多路径增强", ["reasoning", "tot", "self_consistency"]),
    ("根因增强", ["reasoning", "reflexion", "root_cause"]),
    ("幻觉克星", ["fact_verify", "grounding", "debate"]),
    ("全栈P1", ["reasoning", "tot", "self_consistency", "reflexion",
                "root_cause", "rubric_eval", "grounding"]),
    ("全栈P2", ["reasoning", "tot", "self_consistency", "reflexion",
                "root_cause", "rubric_eval", "fact_verify", "grounding", "cross_goal"]),
]

combo_results = []
for name, evos in combos:
    cfg = TaskConfig(name, "goal", N, chain_steps=4, evolutions=evos)
    r = run_batch(cfg, sim_long_reasoning)
    cost_inc = max(r["cost"] - 1, 0.01)
    value = (r["task_acc"] - baseline_r["task_acc"] + baseline_r["步骤_hall"] - r["步骤_hall"]) / cost_inc
    combo_results.append((name, r, value))

combo_results.sort(key=lambda x: x[2], reverse=True)
print(f"  {'组合':<15s} {'任务正确':>8s} {'步骤正确':>8s} {'步骤幻觉':>8s} {'成本':>8s} {'性价比':>8s}")
print(f"  {'─'*15} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
for name, r, value in combo_results:
    print(f"  {name:<15s} {r['task_acc']:>7.1%} {r['步骤_acc']:>7.1%} {r['步骤_hall']:>7.1%} {r['cost']:>7.1f}x {value:>7.1f}")

print(f"\n完成。")
