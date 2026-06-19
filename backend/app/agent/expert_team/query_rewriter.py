"""查询改写器 — 口语化查询 → 精确检索 query

核心思想：
  用户的子任务可能是口语化表达，直接用于向量检索召回率低。
  先用 LLM 改写为精确的检索 query，再去做语义匹配。
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class RewrittenQuery(BaseModel):
    """改写后的查询"""
    queries: list[str] = Field(default_factory=list, description="改写后的查询列表（1-3 个）")
    keywords: list[str] = Field(default_factory=list, description="关键词")


async def rewrite_query(
    db,
    provider_id: int,
    model_name: str,
    original_query: str,
    context: str = "",
    temperature: float = 0.3,
) -> Optional[RewrittenQuery]:
    """将口语化查询改写为精确检索 query

    Args:
        original_query: 原始查询（子任务描述）
        context: 上下文（专家角色等）
    """
    from app.agent.llm_service import llm_service

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        context_section = f"\n\n## 上下文\n{context}" if context else ""

        rewrite_prompt = f"""请将以下查询改写为适合向量检索的精确表达。

## 原始查询
{original_query}
{context_section}

要求：
1. 生成 1-3 个不同角度的检索 query
2. 提取关键词
3. 去除口语化表达，保留核心语义
4. 每个 query 独立可检索"""

        structured_llm = llm.with_structured_output(RewrittenQuery)
        return await structured_llm.ainvoke(rewrite_prompt)

    except Exception as e:
        logger.warning(f"查询改写失败（降级为原始查询）: {e}")
        return None


async def rerank_results(
    db,
    provider_id: int,
    model_name: str,
    query: str,
    candidates: list[dict],
    top_n: int = 3,
    temperature: float = 0.1,
) -> list[dict]:
    """LLM 重排序 — 用 LLM 判断每个候选结果与查询的相关性

    比纯向量距离更准确，尤其是语义复杂时。

    Args:
        query: 原始查询
        candidates: 候选结果列表 [{content, source, score}]
        top_n: 返回 top-n

    Returns:
        重排序后的结果列表
    """
    if len(candidates) <= top_n:
        return candidates

    from app.agent.llm_service import llm_service

    try:
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        candidates_text = "\n".join(
            f"[{i}] {c.get('content', '')[:200]}"
            for i, c in enumerate(candidates)
        )

        rerank_prompt = f"""请评估以下候选结果与查询的相关性，返回最相关的 {top_n} 个。

## 查询
{query}

## 候选结果
{candidates_text}

请返回最相关的 {top_n} 个结果的索引，按相关性从高到低排列。
输出格式: {{"indices": [0, 3, 1]}}"""

        class RerankResult(BaseModel):
            indices: list[int] = Field(default_factory=list)

        structured_llm = llm.with_structured_output(RerankResult)
        result = await structured_llm.ainvoke(rerank_prompt)

        reranked = []
        for idx in result.indices[:top_n]:
            if 0 <= idx < len(candidates):
                reranked.append(candidates[idx])

        return reranked if reranked else candidates[:top_n]

    except Exception as e:
        logger.warning(f"重排序失败（降级为向量排序）: {e}")
        return candidates[:top_n]
