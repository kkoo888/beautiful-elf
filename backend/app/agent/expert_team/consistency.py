"""Self-Consistency 多路径投票 — 生成多条推理链，投票选最佳

核心思想：
  同一个专家对同一个子任务执行 N 次（默认 3 次），
  每次用不同温度生成，然后用 LLM 评估投票选出最佳输出。

前沿依据：
  - Self-Consistency (Wang et al. 2023): 多条推理链投票，GSM8K +17%
  - 实验表明 3-5 条路径即可显著提升准确率

实现策略：
  - 路径数可配（默认 3）
  - 温度递增（0.3, 0.5, 0.7）保证多样性
  - LLM 投票选最佳（不是简单取众数）
  - 成本控制：只在首轮执行时启用，辩论轮不重复
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConsistencyVote(BaseModel):
    """投票结果"""
    best_index: int = Field(..., description="最佳路径索引（0-based）")
    reason: str = Field(default="", description="选择理由")
    scores: list[float] = Field(default_factory=list, description="每条路径的评分")


async def execute_with_self_consistency(
    db,
    provider_id: int,
    model_name: str,
    prompt: str,
    n_paths: int = 3,
    base_temperature: float = 0.3,
    temperature_step: float = 0.2,
    timeout_seconds: int = 120,
) -> tuple[str, int, list[str]]:
    """Self-Consistency 执行：多路径生成 + 投票选最佳

    Args:
        prompt: 专家 prompt
        n_paths: 路径数（默认 3）
        base_temperature: 基础温度
        temperature_step: 温度递增步长

    Returns:
        (最佳输出, 总 token, 所有路径输出)
    """
    import asyncio
    from app.agent.llm_service import llm_service
    from langchain_core.messages import HumanMessage

    all_outputs = []
    total_tokens = 0

    # 生成多条路径
    for i in range(n_paths):
        temp = min(base_temperature + i * temperature_step, 1.0)
        try:
            llm = await llm_service.get_chat_llm(
                db, provider_id=provider_id, model_name=model_name, temperature=temp,
            )
            response = await asyncio.wait_for(
                llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=timeout_seconds,
            )
            content = response.content if isinstance(response.content, str) else str(response.content)
            tokens = getattr(response, "usage_metadata", {})
            if isinstance(tokens, dict):
                total_tokens += tokens.get("total_tokens", 0)

            all_outputs.append(content)

        except Exception as e:
            logger.warning(f"Self-Consistency 路径 {i+1} 失败: {e}")

    if not all_outputs:
        return "", 0, []

    # 只有 1 条路径，直接返回
    if len(all_outputs) == 1:
        return all_outputs[0], total_tokens, all_outputs

    # LLM 投票选最佳
    best_output, best_tokens = await _vote_best(
        db, provider_id, model_name, prompt, all_outputs,
    )
    total_tokens += best_tokens

    return best_output, total_tokens, all_outputs


async def _vote_best(
    db,
    provider_id: int,
    model_name: str,
    original_prompt: str,
    outputs: list[str],
    temperature: float = 0.2,
) -> tuple[str, int]:
    """LLM 投票选出最佳输出"""
    from app.agent.llm_service import llm_service

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        candidates_text = "\n\n".join([
            f"### 方案 {i+1}\n{output[:1500]}"
            for i, output in enumerate(outputs)
        ])

        vote_prompt = f"""以下是同一个任务的多个执行方案，请选出最佳方案。

## 任务
{original_prompt[:500]}

## 方案列表
{candidates_text}

请评估每个方案的：
1. 完整性 — 是否完整回答了任务
2. 准确性 — 内容是否准确
3. 清晰度 — 表达是否清晰

选出最佳方案，输出索引（从 1 开始）。"""

        structured_llm = llm.with_structured_output(ConsistencyVote)
        vote = await structured_llm.ainvoke(vote_prompt)

        # 返回最佳方案
        best_idx = max(0, min(vote.best_index - 1, len(outputs) - 1))
        return outputs[best_idx], 0

    except Exception as e:
        logger.warning(f"投票失败（降级为返回第一条）: {e}")
        return outputs[0], 0
