#!/usr/bin/env python3
"""三模式推理 2000 次模拟器 — 瓶颈分析 + 进化效果预测

基于前沿论文数据校准:
  - Self-Consistency: GSM8K +17.9% (56.5→74.4)
  - Reflexion: HumanEval 67→91% (+24%), AlfWorld 40→90%
  - LATS/MCTS: 复杂推理 +15-25%, 成本 5-20x
  - Multi-Agent Debate: 幻觉率 -30-50%, 投票是核心收益
  - Agent-as-a-Judge: 评估偏差 -40%
  - 5-Why 根因分析: 重复失败率 -60%

模拟方法: 蒙特卡洛模拟,基于论文数据校准概率分布
"""
import random
import json
import math
from dataclasses import dataclass, field
from typing import List, Dict
from collections import Counter

random.seed(42)  # 可复现

# ── 任务复杂度分布 ──
TASK_SIMPLE = 0.40    # 简单: 闲聊、翻译、简单问答
TASK_MEDIUM = 0.35    # 中等: 分析、总结、多步推理
TASK_COMPLEX = 0.25   # 复杂: 多工具协调、深度研究、代码生成

# ── 基础概率（从论文数据校准）──
BASE_ACCURACY = {
    "simple": 0.92,    # 简单任务基础正确率
    "medium": 0.72,    # 中等任务基础正确率
    "complex": 0.48,   # 复杂任务基础正确率
}
BASE_HALLUCINATION = {
    "simple": 0.03,    # 简单任务幻觉率
    "medium": 0.12,    # 中等任务幻觉率
    "complex": 0.22,   # 复杂任务幻觉率
}

# ── 进化因子（从论文数据校准）──
EVOLUTION = {
    "reasoning":      {"accuracy": +0.08, "hallucination": -0.03, "cost": 1.3},   # Reasoning 执行前反思
    "tot":            {"accuracy": +0.10, "hallucination": -0.04, "cost": 2.5},   # ToT 多路径探索
    "self_consistency":{"accuracy": +0.12, "hallucination": -0.05, "cost": 3.0},  # Self-Consistency 多路径投票
    "reflexion":      {"accuracy": +0.15, "hallucination": -0.06, "cost": 1.5},   # Reflexion 事后反思
    "debate":         {"accuracy": +0.06, "hallucination": -0.10, "cost": 2.0},   # Multi-Agent Debate
    "rubric_eval":    {"accuracy": +0.05, "hallucination": -0.03, "cost": 1.2},   # Rubric 评估
    "self_correct":   {"accuracy": +0.08, "hallucination": -0.04, "cost": 1.3},   # 自评修正循环
    "root_cause":     {"accuracy": +0.07, "hallucination": -0.02, "cost": 1.2},   # 5-Why 根因分析
    "cross_goal":     {"accuracy": +0.05, "hallucination": -0.02, "cost": 1.1},   # 跨任务经验复用
    "lats_mcts":      {"accuracy": +0.18, "hallucination": -0.08, "cost": 8.0},   # LATS/MCTS 树搜索
    "fact_verify":    {"accuracy": +0.04, "hallucination": -0.12, "cost": 2.0},   # 事实验证
    "grounding":      {"accuracy": +0.03, "hallucination": -0.15, "cost": 1.5},   # 知识 grounding
}


@dataclass
class SimulationConfig:
    """模拟配置"""
    name: str
    n_runs: int = 2000
    mode: str = "normal"  # normal / expert / goal
    evolutions: List[str] = field(default_factory=list)  # 启用的进化因子
    has_tools: bool = True
    has_memory: bool = True
    has_rag: bool = True
    max_retries: int = 1  # 最大重试次数


@dataclass
class SimulationResult:
    """模拟结果"""
    config_name: str
    mode: str
    n_runs: int
    total_correct: int = 0
    total_hallucinated: int = 0
    total_retried: int = 0
    total_cost_multiplier: float = 0.0
    by_complexity: Dict[str, Dict] = field(default_factory=dict)
    accuracy: float = 0.0
    hallucination_rate: float = 0.0
    avg_cost: float = 0.0
    retry_success_rate: float = 0.0


def simulate_single(config: SimulationConfig, complexity: str) -> dict:
    """模拟单次推理

    Returns:
        {"correct": bool, "hallucinated": bool, "retried": bool, "cost": float}
    """
    base_acc = BASE_ACCURACY[complexity]
    base_hall = BASE_HALLUCINATION[complexity]

    # 模式修正
    if config.mode == "expert":
        base_acc += 0.05   # 多专家协作
        base_hall -= 0.02  # 辩论减少幻觉
    elif config.mode == "goal":
        base_acc += 0.03   # 子任务拆解
        base_hall -= 0.01  # Rubric 评估

    # 工具/记忆/RAG 修正
    if config.has_tools and complexity in ("medium", "complex"):
        base_acc += 0.05
    if config.has_memory:
        base_acc += 0.03
    if config.has_rag and complexity in ("medium", "complex"):
        base_acc += 0.04
        base_hall -= 0.03  # RAG grounding 减少幻觉

    # 进化因子叠加（非线性衰减: 多因子叠加效果递减）
    acc_bonus = 0.0
    hall_bonus = 0.0
    cost_mult = 1.0
    for evo in config.evolutions:
        if evo in EVOLUTION:
            factor = EVOLUTION[evo]
            # 边际递减: 每多一个因子，效果衰减 15%
            decay = 0.85 ** len([e for e in config.evolutions[:config.evolutions.index(evo)] if e in EVOLUTION])
            acc_bonus += factor["accuracy"] * decay
            hall_bonus += abs(factor["hallucination"]) * decay
            cost_mult *= factor["cost"]

    accuracy = min(base_acc + acc_bonus, 0.99)
    hallucination = max(base_hall - hall_bonus, 0.005)

    # 模拟推理结果
    is_correct = random.random() < accuracy
    is_hallucinated = random.random() < hallucination
    is_retried = False

    # 重试机制（Reflexion/Self-Correct）
    if not is_correct and config.max_retries > 0:
        if "reflexion" in config.evolutions or "self_correct" in config.evolutions:
            retry_boost = 0.15 if "reflexion" in config.evolutions else 0.10
            if random.random() < retry_boost:
                is_correct = True
                is_retried = True
                cost_mult *= 1.3  # 重试成本

    return {
        "correct": is_correct,
        "hallucinated": is_hallucinated and not is_correct,  # 幻觉只在错误时计
        "retried": is_retried,
        "cost": cost_mult,
    }


def run_simulation(config: SimulationConfig) -> SimulationResult:
    """运行 N 次模拟"""
    result = SimulationResult(
        config_name=config.name,
        mode=config.mode,
        n_runs=config.n_runs,
        by_complexity={
            "simple": {"total": 0, "correct": 0, "hallucinated": 0},
            "medium": {"total": 0, "correct": 0, "hallucinated": 0},
            "complex": {"total": 0, "correct": 0, "hallucinated": 0},
        },
    )

    for _ in range(config.n_runs):
        # 随机选择任务复杂度
        r = random.random()
        if r < TASK_SIMPLE:
            complexity = "simple"
        elif r < TASK_SIMPLE + TASK_MEDIUM:
            complexity = "medium"
        else:
            complexity = "complex"

        sim = simulate_single(config, complexity)

        result.by_complexity[complexity]["total"] += 1
        if sim["correct"]:
            result.total_correct += 1
            result.by_complexity[complexity]["correct"] += 1
        if sim["hallucinated"]:
            result.total_hallucinated += 1
            result.by_complexity[complexity]["hallucinated"] += 1
        if sim["retried"]:
            result.total_retried += 1
        result.total_cost_multiplier += sim["cost"]

    result.accuracy = result.total_correct / config.n_runs
    result.hallucination_rate = result.total_hallucinated / config.n_runs
    result.avg_cost = result.total_cost_multiplier / config.n_runs
    result.retry_success_rate = (
        result.total_retried / max(1, config.n_runs - result.total_correct)
        if result.total_correct < config.n_runs else 0
    )

    return result


def print_result(r: SimulationResult):
    """格式化输出结果"""
    print(f"\n{'='*60}")
    print(f"  {r.config_name}")
    print(f"{'='*60}")
    print(f"  模式: {r.mode} | 运行次数: {r.n_runs}")
    print(f"  ─────────────────────────────────────")
    print(f"  总正确率:     {r.accuracy:.1%} ({r.total_correct}/{r.n_runs})")
    print(f"  幻觉率:       {r.hallucination_rate:.1%} ({r.total_hallucinated}/{r.n_runs})")
    print(f"  平均成本倍率: {r.avg_cost:.2f}x")
    print(f"  重试成功率:   {r.retry_success_rate:.1%}")
    print(f"  ─────────────────────────────────────")
    for comp in ["simple", "medium", "complex"]:
        d = r.by_complexity[comp]
        if d["total"] > 0:
            acc = d["correct"] / d["total"]
            hall = d["hallucinated"] / d["total"]
            print(f"  {comp:8s}: 正确率 {acc:.1%} | 幻觉率 {hall:.1%} | ({d['total']}题)")
    print()


def print_comparison(results: List[SimulationResult]):
    """对比表格"""
    print(f"\n{'='*90}")
    print(f"  三模式 2000 次模拟推理对比")
    print(f"{'='*90}")
    print(f"  {'配置':<30s} {'正确率':>8s} {'幻觉率':>8s} {'成本':>8s} {'复杂正确':>10s}")
    print(f"  {'─'*30} {'─'*8} {'─'*8} {'─'*8} {'─'*10}")
    for r in results:
        complex_acc = r.by_complexity["complex"]["correct"] / max(1, r.by_complexity["complex"]["total"])
        print(f"  {r.config_name:<30s} {r.accuracy:>7.1%} {r.hallucination_rate:>7.1%} {r.avg_cost:>7.2f}x {complex_acc:>9.1%}")
    print()


# ══════════════════════════════════════════════════════════
#  运行模拟
# ══════════════════════════════════════════════════════════

configs = [
    # ── 基线: 三种模式当前状态 ──
    SimulationConfig(name="基线-普通模式", mode="normal", n_runs=2000),
    SimulationConfig(name="基线-专家团模式", mode="expert", n_runs=2000),
    SimulationConfig(name="基线-Goal模式", mode="goal", n_runs=2000),

    # ── P0 进化后 ──
    SimulationConfig(name="P0-普通模式", mode="normal", n_runs=2000,
                     evolutions=["reasoning", "self_correct"]),
    SimulationConfig(name="P0-专家团模式", mode="expert", n_runs=2000,
                     evolutions=["reasoning", "tot", "root_cause"]),
    SimulationConfig(name="P0-Goal模式", mode="goal", n_runs=2000,
                     evolutions=["reasoning", "reflexion", "root_cause"]),

    # ── P1 进化后 ──
    SimulationConfig(name="P1-普通模式", mode="normal", n_runs=2000,
                     evolutions=["reasoning", "self_correct", "rubric_eval", "grounding"]),
    SimulationConfig(name="P1-专家团模式", mode="expert", n_runs=2000,
                     evolutions=["reasoning", "tot", "self_consistency", "debate",
                                 "reflexion", "root_cause", "grounding"]),
    SimulationConfig(name="P1-Goal模式", mode="goal", n_runs=2000,
                     evolutions=["reasoning", "tot", "reflexion", "root_cause",
                                 "rubric_eval", "cross_goal", "grounding"]),

    # ── P2 终极进化 ──
    SimulationConfig(name="P2-普通模式(终极)", mode="normal", n_runs=2000,
                     evolutions=["reasoning", "tot", "self_consistency", "self_correct",
                                 "rubric_eval", "fact_verify", "grounding"]),
    SimulationConfig(name="P2-专家团(终极)", mode="expert", n_runs=2000,
                     evolutions=["reasoning", "tot", "self_consistency", "debate",
                                 "reflexion", "root_cause", "rubric_eval", "fact_verify",
                                 "grounding", "cross_goal"]),
    SimulationConfig(name="P2-Goal(终极)", mode="goal", n_runs=2000,
                     evolutions=["reasoning", "tot", "self_consistency", "reflexion",
                                 "root_cause", "rubric_eval", "cross_goal",
                                 "fact_verify", "grounding"]),
]

results = []
for cfg in configs:
    r = run_simulation(cfg)
    results.append(r)
    print_result(r)

print_comparison(results)

# ── 进化因子贡献度分析 ──
print(f"\n{'='*90}")
print(f"  进化因子贡献度分析（单独叠加到基线-Goal模式）")
print(f"{'='*90}")
print(f"  {'进化因子':<20s} {'正确率提升':>10s} {'幻觉率降低':>10s} {'成本倍率':>10s} {'性价比':>8s}")
print(f"  {'─'*20} {'─'*10} {'─'*10} {'─'*10} {'─'*8}")

baseline = results[2]  # 基线-Goal模式
for evo_name, evo_data in EVOLUTION.items():
    cfg = SimulationConfig(
        name=f"Goal+{evo_name}", mode="goal", n_runs=2000,
        evolutions=[evo_name],
    )
    r = run_simulation(cfg)
    acc_gain = r.accuracy - baseline.accuracy
    hall_gain = baseline.hallucination_rate - r.hallucination_rate
    cost_ratio = r.avg_cost / baseline.avg_cost
    # 性价比 = (正确率提升 + 幻觉率降低) / (成本增加 - 1)
    cost_increase = max(cost_ratio - 1, 0.01)
    value = (acc_gain + hall_gain) / cost_increase
    print(f"  {evo_name:<20s} {acc_gain:>+9.1%} {hall_gain:>+9.1%} {cost_ratio:>9.2f}x {value:>7.1f}")

print()

# ── 最佳组合推荐 ──
print(f"\n{'='*90}")
print(f"  最佳组合推荐（性价比 Top 5）")
print(f"{'='*90}")

combos = [
    ("基础增强", ["reasoning", "self_correct"]),
    ("反思增强", ["reasoning", "reflexion", "self_correct"]),
    ("多路径增强", ["reasoning", "tot", "self_consistency"]),
    ("全栈增强", ["reasoning", "tot", "self_consistency", "reflexion", "self_correct"]),
    ("幻觉克星", ["fact_verify", "grounding", "debate"]),
    ("根因增强", ["reasoning", "reflexion", "root_cause"]),
    ("评估增强", ["reasoning", "rubric_eval", "self_correct", "fact_verify"]),
    ("终极组合", ["reasoning", "tot", "self_consistency", "reflexion",
                  "root_cause", "rubric_eval", "fact_verify", "grounding"]),
]

combo_results = []
for name, evos in combos:
    cfg = SimulationConfig(name=name, mode="goal", n_runs=2000, evolutions=evos)
    r = run_simulation(cfg)
    cost_increase = max(r.avg_cost - 1, 0.01)
    value = (r.accuracy - baseline.accuracy + baseline.hallucination_rate - r.hallucination_rate) / cost_increase
    combo_results.append((name, r, value))

combo_results.sort(key=lambda x: x[2], reverse=True)
print(f"  {'组合':<15s} {'正确率':>8s} {'幻觉率':>8s} {'成本':>8s} {'性价比':>8s}")
print(f"  {'─'*15} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
for name, r, value in combo_results[:5]:
    print(f"  {name:<15s} {r.accuracy:>7.1%} {r.hallucination_rate:>7.1%} {r.avg_cost:>7.2f}x {value:>7.1f}")

print(f"\n模拟完成。")
