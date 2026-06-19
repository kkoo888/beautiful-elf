"""Reflexion 事后反思 — 从执行结果中学习

核心思想：
  专家执行完后，不管成功还是失败，都生成结构化反思：
  - 做对了什么？
  - 做错了什么？
  - 下次应该怎么做？
  反思结果存入记忆，下次执行时自动召回。

前沿依据：
  - Reflexion (Shinn et al. 2023): 语言反馈强化 Agent 决策
  - 实验表明 Reflexion 在 HumanEval 上提升 20%+

与 Reasoning 的区别：
  - Reasoning = 执行前思考（预判）
  - Reflexion = 执行后反思（复盘）
  两者形成完整闭环：反思 → 记忆 → 召回 → 下次 Reasoning
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class Reflexion(BaseModel):
    """事后反思"""
    success: bool = Field(..., description="是否成功完成任务")
    what_worked: list[str] = Field(default_factory=list, description="做对了什么")
    what_failed: list[str] = Field(default_factory=list, description="做错了什么")
    key_insights: list[str] = Field(default_factory=list, description="关键洞察")
    next_time_improvements: list[str] = Field(default_factory=list, description="下次改进建议")
    confidence: float = Field(default=0.5, ge=0, le=1, description="反思置信度")


async def generate_reflexion(
    db,
    provider_id: int,
    model_name: str,
    expert_name: str,
    expert_role: str,
    subtask: str,
    output: str,
    guardrail_passed: bool = True,
    guardrail_errors: list[str] = None,
    duration_ms: int = 0,
    temperature: float = 0.3,
) -> Optional[Reflexion]:
    """生成事后反思

    Args:
        expert_name: 专家名称
        expert_role: 专家角色
        subtask: 子任务
        output: 专家输出
        guardrail_passed: Guardrail 是否通过
        guardrail_errors: Guardrail 错误列表
        duration_ms: 执行耗时
    """
    from app.agent.llm_service import llm_service

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        guardrail_section = ""
        if not guardrail_passed and guardrail_errors:
            errors_text = "\n".join(f"  - {e}" for e in guardrail_errors)
            guardrail_section = f"\n\n## 质量校验结果\n未通过，问题：\n{errors_text}"

        duration_note = f"\n执行耗时: {duration_ms}ms" if duration_ms > 0 else ""

        reflexion_prompt = f"""你是{expert_name}，角色是{expert_role}。
你刚刚完成了一个任务，请认真反思。

## 任务
{subtask}

## 你的输出
{output[:2000]}
{guardrail_section}{duration_note}

请从以下维度反思：

1. **做对了什么？** — 哪些分析/结论是有价值的？
2. **做错了什么？** — 哪些地方有问题或遗漏？
3. **关键洞察** — 从这次执行中学到了什么？
4. **下次改进** — 如果重新做这个任务，你会怎么改？

请诚实反思，不要只说好话。"""

        structured_llm = llm.with_structured_output(Reflexion)
        reflexion = await structured_llm.ainvoke(reflexion_prompt)
        reflexion.success = guardrail_passed

        # 根据执行质量调整置信度
        if guardrail_passed and duration_ms < 30000:
            reflexion.confidence = min(reflexion.confidence + 0.2, 1.0)
        elif not guardrail_passed:
            reflexion.confidence = max(reflexion.confidence - 0.2, 0.0)

        return reflexion

    except Exception as e:
        logger.warning(f"反思生成失败（非致命）: {e}")
        return None


def format_reflexion_for_prompt(reflexion: Optional[Reflexion]) -> str:
    """将反思格式化为 prompt 注入文本（供下次执行使用）"""
    if not reflexion:
        return ""

    worked = "\n".join(f"  ✅ {w}" for w in reflexion.what_worked) if reflexion.what_worked else "  无"
    failed = "\n".join(f"  ❌ {f}" for f in reflexion.what_failed) if reflexion.what_failed else "  无"
    insights = "\n".join(f"  💡 {i}" for i in reflexion.key_insights) if reflexion.key_insights else "  无"
    improvements = "\n".join(f"  📌 {i}" for i in reflexion.next_time_improvements) if reflexion.next_time_improvements else "  无"

    return f"""
## 历史反思（上次执行经验）
**做对了:**
{worked}
**做错了:**
{failed}
**关键洞察:**
{insights}
**本次改进:**
{improvements}"""


async def store_reflexion_as_memory(
    expert_id: int,
    team_id: int,
    reflexion: Reflexion,
    db=None,
) -> int:
    """将反思结果存入记忆系统

    每个反思点作为一条独立的原子事实存储，分类为 insight/risk/pattern。
    """
    from app.agent.expert_team.memory import AtomicFact, store_experience

    facts = []

    # 做对了 → insight
    for w in reflexion.what_worked:
        facts.append(AtomicFact(content=w, category="insight", importance=0.7))

    # 做错了 → risk
    for f in reflexion.what_failed:
        facts.append(AtomicFact(content=f, category="risk", importance=0.8))

    # 关键洞察 → insight
    for i in reflexion.key_insights:
        facts.append(AtomicFact(content=i, category="insight", importance=0.9))

    # 改进建议 → pattern
    for i in reflexion.next_time_improvements:
        facts.append(AtomicFact(content=i, category="pattern", importance=0.8))

    if not facts:
        return 0

    return await store_experience(expert_id, team_id, facts, db=db)
