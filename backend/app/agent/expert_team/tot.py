"""Tree of Thoughts (ToT) — 树状搜索多条推理路径

核心思想：
  不同于线性推理（CoT），ToT 在每个决策点生成多个分支，
  自我评估每个分支的质量，选择最优路径继续。

前沿依据：
  - Tree of Thoughts (Yao et al. 2023): 在 Game of 24 上从 4% → 74%
  - LATS (Zhou et al. 2023): 蒙特卡洛树搜索 + LLM 评估

实现策略（轻量版）：
  1. 专家收到子任务后，生成 3 个不同角度的初始思路
  2. LLM 评估每个思路的可行性（1-10 分）
  3. 选择最优思路，生成详细执行方案
  4. 将方案注入专家 prompt

与 Self-Consistency 的区别：
  - Self-Consistency: 同一个 prompt 执行多次，投票选最佳
  - ToT: 在思考阶段分叉，评估后选择最优路径再执行
  - ToT 更省 token（只在思考阶段分叉，执行阶段只执行一次）
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class ThoughtBranch(BaseModel):
    """思维分支"""
    approach: str = Field(..., description="思路描述")
    pros: list[str] = Field(default_factory=list, description="优点")
    cons: list[str] = Field(default_factory=list, description="缺点")
    feasibility_score: float = Field(default=5.0, ge=1, le=10, description="可行性评分 1-10")
    expected_quality: float = Field(default=5.0, ge=1, le=10, description="预期质量 1-10")


class ThoughtEvaluation(BaseModel):
    """思维评估结果"""
    branches: list[ThoughtBranch] = Field(default_factory=list, description="所有分支")
    best_index: int = Field(default=0, description="最佳分支索引")
    reasoning: str = Field(default="", description="选择理由")


async def explore_thoughts(
    db,
    provider_id: int,
    model_name: str,
    expert_name: str,
    expert_role: str,
    subtask: str,
    context: str = "",
    n_branches: int = 3,
    temperature: float = 0.7,
) -> Optional[ThoughtEvaluation]:
    """探索多条思维路径并选择最优

    Args:
        expert_name: 专家名称
        expert_role: 专家角色
        subtask: 子任务
        context: 上下文
        n_branches: 分支数（默认 3）
    """
    from app.agent.llm_service import llm_service

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        context_section = f"\n\n## 上下文\n{context}" if context else ""

        explore_prompt = f"""你是{expert_name}，角色是{expert_role}。
请为以下任务思考 {n_branches} 个不同的执行思路。

## 任务
{subtask}
{context_section}

请从不同角度思考：
- 思路 1：从最直接/常规的角度
- 思路 2：从创新/非常规的角度
- 思路 3：从风险防范/保守的角度

每个思路请评估：
1. 优点
2. 缺点
3. 可行性（1-10）
4. 预期质量（1-10）

最后选出最佳思路。"""

        structured_llm = llm.with_structured_output(ThoughtEvaluation)
        evaluation = await structured_llm.ainvoke(explore_prompt)

        # 确保 best_index 在范围内
        if evaluation.branches:
            evaluation.best_index = max(0, min(evaluation.best_index, len(evaluation.branches) - 1))

        return evaluation

    except Exception as e:
        logger.warning(f"ToT 探索失败（降级为线性推理）: {e}")
        return None


def format_tot_for_prompt(evaluation: Optional[ThoughtEvaluation]) -> str:
    """将 ToT 评估结果格式化为 prompt 注入文本"""
    if not evaluation or not evaluation.branches:
        return ""

    best = evaluation.branches[evaluation.best_index] if evaluation.best_index < len(evaluation.branches) else None
    if not best:
        return ""

    pros = "\n".join(f"  ✅ {p}" for p in best.pros) if best.pros else "  无"
    cons = "\n".join(f"  ⚠️ {c}" for c in best.cons) if best.cons else "  无"

    return f"""
## 思维路径分析（Tree of Thoughts）
**选定思路:** {best.approach}
**可行性:** {best.feasibility_score:.0f}/10 | **预期质量:** {best.expected_quality:.0f}/10

**优点:**
{pros}
**需要注意:**
{cons}

**选择理由:** {evaluation.reasoning}"""
