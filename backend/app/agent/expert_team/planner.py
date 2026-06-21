"""专家团任务规划器 — 为每个专家生成 step-by-step 执行计划

核心思想：
  PM 分配子任务后，Planner 为每个子任务生成结构化的执行步骤，
  注入专家 prompt，让专家「按计划行动」而非「自由发挥」。
"""
import json
import re
from typing import Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class ExpertPlanStep(BaseModel):
    """单个执行步骤"""
    step: int = Field(..., description="步骤序号")
    action: str = Field(..., description="具体行动")
    expected_output: str = Field(default="", description="预期产出")


class ExpertPlan(BaseModel):
    """专家执行计划"""
    objective: str = Field(..., description="核心目标")
    steps: list[ExpertPlanStep] = Field(default_factory=list, description="执行步骤")
    risk_notes: str = Field(default="", description="风险提示")


async def generate_expert_plan(
    db,
    provider_id: int,
    model_name: str,
    expert_name: str,
    expert_role: str,
    expert_goal: str,
    subtask: str,
    context: str = "",
    memory_context: str = "",
    temperature: float = 0.5,
) -> Optional[ExpertPlan]:
    """为单个专家生成执行计划

    Args:
        expert_name: 专家名称
        expert_role: 专家角色
        expert_goal: 专家目标
        subtask: PM 分配的子任务
        context: 之前讨论的上下文
        memory_context: 相关记忆上下文
    """
    from app.agent.llm_service import llm_service

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        context_section = f"\n\n## 之前讨论\n{context}" if context else ""
        memory_section = f"\n\n## 相关经验\n{memory_context}" if memory_context else ""

        plan_prompt = f"""你是任务规划专家。请为以下专家生成结构化的执行计划。

## 专家信息
- 名称: {expert_name}
- 角色: {expert_role}
- 目标: {expert_goal or '完成子任务'}

## 子任务
{subtask}
{context_section}
{memory_section}

请生成执行计划，输出 JSON：
{{"objective": "核心目标", "steps": [{{"step": 1, "action": "具体行动", "expected_output": "预期产出"}}], "risk_notes": "风险提示"}}

要求：
1. 步骤 3-10 个，每个步骤是具体可执行的行动
2. 步骤之间有逻辑递进关系
3. 最后一步应该是输出/总结
4. 风险提示简明扼要"""

        structured_llm = llm.with_structured_output(ExpertPlan)
        plan = await structured_llm.ainvoke(plan_prompt)
        return plan

    except Exception as e:
        logger.warning(f"计划生成失败（降级为无计划执行）: {e}")
        return None


def format_plan_for_prompt(plan: Optional[ExpertPlan]) -> str:
    """将计划格式化为 prompt 注入文本"""
    if not plan or not plan.steps:
        return ""

    steps_text = "\n".join(
        f"  {s.step}. {s.action}" + (f" → 预期产出: {s.expected_output}" if s.expected_output else "")
        for s in plan.steps
    )
    risk_text = f"\n⚠️ 风险提示: {plan.risk_notes}" if plan.risk_notes else ""

    return f"""
## 执行计划
目标: {plan.objective}
{steps_text}{risk_text}

请按以上步骤有序执行。"""
