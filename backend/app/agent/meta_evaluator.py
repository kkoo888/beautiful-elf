"""元评估器 — 评估评估器的质量，检测系统性偏差

核心思想:
  评估器本身可能有偏差（过于宽松/严格），
  元评估器分析历史评估记录，检测偏差并给出校准建议。

前沿依据:
  - Agent-as-a-Judge (2024): 用 Agent 评估 Agent
  - Multi-Agent-as-Judge (2025): 多评估 Agent + 仲裁
  - CollabEval (2026): 三阶段协作评估

实现:
  1. 统计分析: 分数分布、通过率、偏差方向
  2. LLM 分析: 评估标准是否合理、是否有系统性遗漏
  3. 校准建议: 调整阈值、增加评估维度
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class MetaEvaluationResult(BaseModel):
    """元评估结果"""
    bias_direction: str = Field(description="偏差方向: too_lenient/too_strict/balanced")
    calibration_score: float = Field(ge=0, le=1, description="校准分数 0-1")
    false_positive_rate: float = Field(default=0.0, description="误判通过率（应拒绝但通过）")
    false_negative_rate: float = Field(default=0.0, description="误判拒绝率（应通过但拒绝）")
    consistency_score: float = Field(default=0.5, ge=0, le=1, description="评估一致性")
    recommendation: str = Field(description="校准建议")
    suggested_threshold: Optional[float] = Field(default=None, description="建议的通过阈值")


async def meta_evaluate(
    llm,
    evaluations: list[dict],
    temperature: float = 0.2,
) -> Optional[MetaEvaluationResult]:
    """元评估 — 分析评估记录的系统性偏差

    Args:
        llm: LLM 实例
        evaluations: 历史评估记录 [{score, passed, reason, ...}]
        temperature: LLM 温度
    """
    if not evaluations or len(evaluations) < 3:
        return None

    try:
        scores = [e.get("score", 5) for e in evaluations]
        passed = [e.get("passed", False) for e in evaluations]

        avg_score = sum(scores) / len(scores)
        pass_rate = sum(passed) / len(passed)
        score_std = (sum((s - avg_score) ** 2 for s in scores) / len(scores)) ** 0.5

        # 分数分布
        distribution = {}
        for s in scores:
            bucket = f"{int(s)}-{int(s)+1}"
            distribution[bucket] = distribution.get(bucket, 0) + 1

        # 统计偏差
        bias = "balanced"
        if avg_score > 7.5 and pass_rate > 0.85:
            bias = "too_lenient"
        elif avg_score < 4.5 and pass_rate < 0.25:
            bias = "too_strict"

        prompt = f"""分析以下评估记录的质量和偏差:

评估次数: {len(evaluations)}
平均分: {avg_score:.1f}/10
通过率: {pass_rate:.1%}
分数标准差: {score_std:.1f}
分数分布: {distribution}

请判断:
1. 评估器是否有系统性偏差？
2. 通过阈值是否合理？
3. 是否有评估不一致的情况？
4. 如何校准？

输出 JSON: {{"bias_direction": "too_lenient/too_strict/balanced", "calibration_score": 0.8, "recommendation": "...", "suggested_threshold": 6.0}}"""

        structured = llm.with_structured_output(MetaEvaluationResult)
        result = await structured.ainvoke(prompt)

        # 用统计结果补充
        result.false_positive_rate = _estimate_fpr(scores, passed)
        result.false_negative_rate = _estimate_fnr(scores, passed)
        result.consistency_score = max(0, 1 - score_std / 5)

        logger.info(f"[meta_eval] 偏差={result.bias_direction} 校准={result.calibration_score:.2f}")
        return result

    except Exception as e:
        logger.warning(f"[meta_eval] 元评估失败: {e}")
        return None


def _estimate_fpr(scores: list, passed: list) -> float:
    """估算误判通过率: 低分但通过"""
    fp = sum(1 for s, p in zip(scores, passed) if p and s < 5)
    total_passed = sum(passed)
    return fp / max(total_passed, 1)


def _estimate_fnr(scores: list, passed: list) -> float:
    """估算误判拒绝率: 高分但未通过"""
    fn = sum(1 for s, p in zip(scores, passed) if not p and s >= 7)
    total_failed = sum(1 for p in passed if not p)
    return fn / max(total_failed, 1)


def format_meta_eval_for_prompt(result: Optional[MetaEvaluationResult]) -> str:
    if not result:
        return ""
    bias_map = {"too_lenient": "过于宽松", "too_strict": "过于严格", "balanced": "均衡"}
    return f"""
## 评估校准提示
- 评估偏差: {bias_map.get(result.bias_direction, result.bias_direction)}
- 校准分数: {result.calibration_score:.0%}
- 建议: {result.recommendation}"""
