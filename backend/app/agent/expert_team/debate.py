"""多智能体辩论机制 — 交叉验证减少幻觉

核心思想：
  专家独立执行完后，将自己的输出发给其他专家审阅。
  每个专家可以质疑、补充、修正其他人的观点。
  达成共识或辩论轮次结束后，PM 汇总。

前沿依据：
  - iMAD (2025): Multi-Agent Debate 提升推理准确率 GSM8K +5.7%, MATH +8.2%
  - MACA (2025): Multi-Agent Consensus Alignment 通过 RL 训练模型利用辩论结果
  - Du et al. (2024): 辩论机制显著减少幻觉率

辩论流程：
  Round 1: 专家独立执行，输出初始观点
  Round 2: 每个专家审阅其他人的观点，输出质疑/补充/修正
  Round 3: 每个专家根据反馈修正自己的观点
  Final: PM 汇总所有观点和辩论记录
"""
import json
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class DebateReview(BaseModel):
    """辩论审阅结果"""
    reviewer_name: str = Field(..., description="审阅者名称")
    reviewer_role: str = Field(..., description="审阅者角色")
    target_name: str = Field(..., description="被审阅者名称")
    agreements: list[str] = Field(default_factory=list, description="认同的观点")
    challenges: list[str] = Field(default_factory=list, description="质疑的观点")
    supplements: list[str] = Field(default_factory=list, description="补充的观点")
    overall_assessment: str = Field(default="", description="总体评价")


class DebateRoundResult(BaseModel):
    """辩论轮次结果"""
    round_num: int
    reviews: list[DebateReview] = Field(default_factory=list)
    consensus_level: float = Field(default=0.0, ge=0, le=1, description="共识程度 0-1")


class RevisedOpinion(BaseModel):
    """修正后的观点"""
    expert_name: str
    original_summary: str = Field(default="", description="原始观点摘要")
    revised_content: str = Field(default="", description="修正后的内容")
    changes: list[str] = Field(default_factory=list, description="修改说明")


async def run_debate_round(
    db,
    provider_id: int,
    model_name: str,
    expert_results: list[dict],
    max_review_targets: int = 3,
    temperature: float = 0.4,
) -> Optional[DebateRoundResult]:
    """执行一轮辩论

    每个专家审阅其他人的输出，产出质疑/补充/修正。

    Args:
        expert_results: [{expert_name, expert_role, subtask, output}]
        max_review_targets: 每个专家最多审阅几个其他人
    """
    from app.agent.llm_service import llm_service

    if len(expert_results) < 2:
        return None  # 少于 2 个专家，无法辩论

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        reviews = []

        for reviewer in expert_results:
            # 选择审阅目标（跳过自己，最多 max_review_targets 个）
            targets = [t for t in expert_results if t["expert_name"] != reviewer["expert_name"]]
            targets = targets[:max_review_targets]

            if not targets:
                continue

            targets_text = "\n\n".join([
                f"### {t['expert_name']}({t['expert_role']}) — 子任务: {t['subtask']}\n{t['output'][:1500]}"
                for t in targets
            ])

            review_prompt = f"""你是{reviewer['expert_name']}，角色是{reviewer['expert_role']}。
你刚刚完成了自己的任务，现在请审阅其他专家的分析结果。

## 你的专业领域
{reviewer.get('subtask', '')}

## 其他专家的分析
{targets_text}

请从你的专业角度审阅每个专家的输出：
1. 你认同哪些观点？（具体列出）
2. 你质疑哪些观点？（给出理由）
3. 你有什么补充？（他们遗漏了什么）
4. 总体评价

请用 JSON 格式输出，每个被审阅者一条。"""

            class ReviewBatch(BaseModel):
                reviews: list[DebateReview] = Field(default_factory=list)

            structured_llm = llm.with_structured_output(ReviewBatch)
            batch = await structured_llm.ainvoke(review_prompt)

            # 确保 reviewer_name 和 reviewer_role 正确
            for r in batch.reviews:
                r.reviewer_name = reviewer["expert_name"]
                r.reviewer_role = reviewer["expert_role"]

            reviews.extend(batch.reviews)

        # 计算共识程度
        total_challenges = sum(len(r.challenges) for r in reviews)
        total_agreements = sum(len(r.agreements) for r in reviews)
        total = total_challenges + total_agreements
        consensus_level = total_agreements / total if total > 0 else 1.0

        return DebateRoundResult(
            round_num=1,
            reviews=reviews,
            consensus_level=consensus_level,
        )

    except Exception as e:
        logger.warning(f"辩论轮次执行失败: {e}")
        return None


async def revise_opinion(
    db,
    provider_id: int,
    model_name: str,
    expert_name: str,
    expert_role: str,
    original_output: str,
    reviews_received: list[DebateReview],
    temperature: float = 0.5,
) -> Optional[RevisedOpinion]:
    """根据辩论反馈修正观点

    Args:
        expert_name: 专家名称
        expert_role: 专家角色
        original_output: 原始输出
        reviews_received: 收到的审阅反馈
    """
    from app.agent.llm_service import llm_service

    if not reviews_received:
        return None

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        reviews_text = "\n\n".join([
            f"**{r.reviewer_name}({r.reviewer_role})**:\n"
            + (f"  认同: {', '.join(r.agreements)}\n" if r.agreements else "")
            + (f"  质疑: {', '.join(r.challenges)}\n" if r.challenges else "")
            + (f"  补充: {', '.join(r.supplements)}\n" if r.supplements else "")
            for r in reviews_received
        ])

        revise_prompt = f"""你是{expert_name}，角色是{expert_role}。
你之前的分析收到了其他专家的反馈，请根据反馈修正你的观点。

## 你之前的分析
{original_output[:2000]}

## 其他专家的反馈
{reviews_text}

请：
1. 保留你认同且未被质疑的观点
2. 回应质疑：如果质疑有道理，修正；如果质疑不成立，解释原因
3. 纳入有价值的补充
4. 输出修正后的完整分析"""

        structured_llm = llm.with_structured_output(RevisedOpinion)
        revised = await structured_llm.ainvoke(revise_prompt)
        revised.expert_name = expert_name
        return revised

    except Exception as e:
        logger.warning(f"观点修正失败: {e}")
        return None


def format_debate_for_prompt(debate_result: Optional[DebateRoundResult]) -> str:
    """将辩论结果格式化为 prompt 注入文本"""
    if not debate_result or not debate_result.reviews:
        return ""

    reviews_text = []
    for r in debate_result.reviews:
        parts = [f"**{r.reviewer_name}({r.reviewer_role})** 审阅 **{r.target_name}**:"]
        if r.agreements:
            parts.append(f"  ✅ 认同: {'; '.join(r.agreements)}")
        if r.challenges:
            parts.append(f"  ❌ 质疑: {'; '.join(r.challenges)}")
        if r.supplements:
            parts.append(f"  💡 补充: {'; '.join(r.supplements)}")
        reviews_text.append("\n".join(parts))

    return f"""
## 专家辩论记录（共识程度: {debate_result.consensus_level:.0%}）
{chr(10).join(reviews_text)}"""


def format_revised_opinions(opinions: list[RevisedOpinion]) -> str:
    """将修正后的观点格式化"""
    if not opinions:
        return ""

    parts = []
    for o in opinions:
        parts.append(f"### {o.expert_name}（修正后）\n{o.revised_content}")
        if o.changes:
            parts.append(f"修改说明: {'; '.join(o.changes)}")

    return "\n\n".join(parts)
