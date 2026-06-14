"""RRF 融合 — Reciprocal Rank Fusion 纯函数

解决 BM25 分数（无界正整数）和向量相似度（[-1,1]）不可比问题。
公式: score(d) = Σ 1/(k + rank_i(d))，k 通常取 60
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hit:
    """检索命中记录"""
    doc_id: str
    rank: int       # 1-based
    score: float    # 仅用于调试/观测


def rrf(rankings: list[list[Hit]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion — 多路排名融合

    Args:
        rankings: 多个检索器的排名列表，每个列表按相关性降序排列
        k: 平滑参数，通常取 60（论文推荐值）

    Returns:
        融合后的 (doc_id, score) 列表，按分数降序排列

    示例:
        bm25_hits = [Hit("doc1", 1, 0.9), Hit("doc2", 2, 0.7)]
        vec_hits  = [Hit("doc2", 1, 0.95), Hit("doc1", 2, 0.8)]
        fused = rrf([bm25_hits, vec_hits])
        # doc2 排第一（两路都排在前面）
    """
    scores: dict[str, float] = {}
    for ranked in rankings:
        for hit in ranked:
            scores[hit.doc_id] = scores.get(hit.doc_id, 0.0) + 1.0 / (k + hit.rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
