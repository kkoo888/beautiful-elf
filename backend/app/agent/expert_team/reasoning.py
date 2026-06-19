"""专家团执行前反思 — 让专家先思考再行动

核心思想：
  收到子任务后，先用低温度 LLM 做一轮结构化反思：
  - 核心挑战是什么？
  - 应该用哪些能力/工具？
  - 有什么风险？
  - 执行策略是什么？
  然后将反思结果注入执行 prompt。
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class ExpertReasoning(BaseModel):
    """专家执行前反思"""
    challenges: list[str] = Field(default_factory=list, description="核心挑战")
    strategy: str = Field(default="", description="执行策略")
    tools_to_use: list[str] = Field(default_factory=list, description="应使用的工具/技能")
    risks: list[str] = Field(default_factory=list, description="潜在风险")
    key_points: list[str] = Field(default_factory=list, description="关键要点")


async def generate_reasoning(
    db,
    provider_id: int,
    model_name: str,
    expert_name: str,
    expert_role: str,
    expert_goal: str,
    subtask: str,
    skills_desc: str = "",
    context: str = "",
    temperature: float = 0.3,
) -> Optional[ExpertReasoning]:
    """执行前反思

    Args:
        expert_name: 专家名称
        expert_role: 专家角色
        expert_goal: 专家目标
        subtask: 子任务
        skills_desc: 可用技能描述
        context: 上下文
    """
    from app.agent.llm_service import llm_service

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        skills_section = f"\n\n## 可用技能\n{skills_desc}" if skills_desc else ""
        context_section = f"\n\n## 上下文\n{context}" if context else ""

        reasoning_prompt = f"""你是{expert_name}，角色是{expert_role}。
目标: {expert_goal or '完成子任务'}

## 子任务
{subtask}
{skills_section}{context_section}

请先思考再行动。分析以下维度：

1. **核心挑战**: 这个任务最难的部分是什么？
2. **执行策略**: 你应该采用什么方法？
3. **工具选择**: 应该用哪些技能/工具？
4. **风险识别**: 有什么潜在风险或陷阱？
5. **关键要点**: 输出时必须包含的关键信息

请用 JSON 格式输出你的思考。"""

        structured_llm = llm.with_structured_output(ExpertReasoning)
        reasoning = await structured_llm.ainvoke(reasoning_prompt)
        return reasoning

    except Exception as e:
        logger.warning(f"反思生成失败（降级为无反思执行）: {e}")
        return None


def format_reasoning_for_prompt(reasoning: Optional[ExpertReasoning]) -> str:
    """将反思结果格式化为 prompt 注入文本"""
    if not reasoning:
        return ""

    challenges = "\n".join(f"  - {c}" for c in reasoning.challenges) if reasoning.challenges else "  无"
    tools = ", ".join(reasoning.tools_to_use) if reasoning.tools_to_use else "无特殊要求"
    risks = "\n".join(f"  - {r}" for r in reasoning.risks) if reasoning.risks else "  无"
    key_points = "\n".join(f"  - {p}" for p in reasoning.key_points) if reasoning.key_points else "  无"

    return f"""
## 执行前思考
**核心挑战:**
{challenges}

**执行策略:** {reasoning.strategy}

**推荐工具:** {tools}

**风险提示:**
{risks}

**关键要点:**
{key_points}"""
