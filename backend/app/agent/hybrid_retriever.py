"""HybridRetriever — 混合检索控制器（BM25 + 向量 + RRF）

策略: "lexical" | "semantic" | "hybrid"（默认 hybrid）
自动降级: embedding 不可用 → 退回 lexical-only
"""
from __future__ import annotations

import threading
from typing import Literal

from app.core.logging import get_logger
from app.agent.bm25_retriever import BM25Retriever
from app.agent.rrf_fusion import Hit, rrf as rrf_fusion

log = get_logger(__name__)

Strategy = Literal["lexical", "semantic", "hybrid"]


class HybridRetriever:
    """混合检索：BM25 关键词 + 向量语义 → RRF 融合

    用法:
        hybrid = HybridRetriever(vector_retriever, strategy="hybrid")
        hybrid.index(chunks)  # 构建 BM25 索引
        hits = hybrid.retrieve("查询文本", top_k=20)
    """

    def __init__(
        self,
        vector_retriever=None,       # LlamaIndex VectorIndexRetriever
        rrf_k: int = 60,
        lexical_top_n: int = 20,
        semantic_top_n: int = 20,
        strategy: Strategy = "hybrid",
    ):
        self._rrf_k = rrf_k
        self._lex_top_n = lexical_top_n
        self._sem_top_n = semantic_top_n
        self._strategy = strategy
        self._final_top_k = max(lexical_top_n, semantic_top_n)  # RRF 融合后最终返回数
        self._lock = threading.Lock()

        # BM25 检索器
        self._bm25 = BM25Retriever()
        self._bm25_fp: str | None = None

        # 向量检索器（LlamaIndex retriever）
        self._vector_retriever = vector_retriever
        self._vector_available = vector_retriever is not None

    def index(self, chunks: list[dict]):
        """构建 BM25 索引

        Args:
            chunks: [{"chunk_id": str, "filename": str, "content": str, "document_id": int}, ...]
        """
        with self._lock:
            self._bm25.index(chunks)
            self._bm25_fp = str(len(chunks))
            log.info(f"[hybrid] BM25 索引就绪: {len(chunks)} 个分块")

    def add_chunks(self, chunks: list[dict]):
        """增量添加分块到 BM25 索引"""
        with self._lock:
            for chunk in chunks:
                self._bm25.add_chunk(chunk)

    def remove_by_doc_id(self, doc_id: str):
        """删除指定文档的 BM25 索引"""
        with self._lock:
            self._bm25.remove_by_doc_id(doc_id)

    def set_vector_retriever(self, retriever):
        """动态设置向量检索器"""
        with self._lock:
            self._vector_retriever = retriever
            self._vector_available = retriever is not None

    def retrieve(self, query: str, top_k: int = 20) -> list[Hit]:
        """混合检索: BM25 + 向量 → RRF 融合

        自动降级策略:
        - strategy="hybrid": 两路都用，任一失败自动降级
        - strategy="lexical": 只用 BM25
        - strategy="semantic": 只用向量，失败降级 BM25
        """
        if not query or not query.strip():
            return []

        # ── 选择活跃检索源 ──
        use_lexical, use_semantic = self._select_sources()

        rankings: list[list[Hit]] = []

        # ── BM25 检索 ──
        if use_lexical and self._bm25.is_ready:
            lex_hits = self._bm25.search(query, top_n=self._lex_top_n)
            if lex_hits:
                rankings.append(lex_hits)
                log.debug(f"[hybrid] BM25 返回 {len(lex_hits)} 个结果")

        # ── 向量检索 ──
        sem_failed = False
        if use_semantic and self._vector_available:
            try:
                sem_hits = self._vector_search(query, top_n=self._sem_top_n)
                if sem_hits:
                    rankings.append(sem_hits)
                    log.debug(f"[hybrid] 向量检索返回 {len(sem_hits)} 个结果")
            except (ImportError, OSError) as exc:
                # 永久失败：embedding 模型不可用
                log.error(f"[hybrid] 向量检索永久失败: {exc}")
                self._vector_available = False
                sem_failed = True
            except Exception as exc:
                # 临时失败：下次重试
                log.warning(f"[hybrid] 向量检索临时失败: {exc}")
                sem_failed = True

        # strategy="semantic" 失败 → 降级 BM25
        if self._strategy == "semantic" and sem_failed and self._bm25.is_ready:
            lex_hits = self._bm25.search(query, top_n=self._lex_top_n)
            if lex_hits:
                rankings.append(lex_hits)

        # ── RRF 融合 ──
        rankings = [r for r in rankings if r]
        if not rankings:
            log.warning("[hybrid] 所有检索源均无结果")
            return []

        fused = rrf_fusion(rankings, k=self._rrf_k)
        return [
            Hit(doc_id=doc_id, rank=i + 1, score=score)
            for i, (doc_id, score) in enumerate(fused[:top_k])
        ]

    def _select_sources(self) -> tuple[bool, bool]:
        """根据策略选择检索源"""
        if self._strategy == "lexical":
            return True, False
        elif self._strategy == "semantic":
            return False, self._vector_available
        else:  # "hybrid"
            return True, self._vector_available

    def _vector_search(self, query: str, top_n: int) -> list[Hit]:
        """调用 LlamaIndex 向量检索器，转换为 Hit 格式"""
        from llama_index.core.schema import QueryBundle

        nodes = self._vector_retriever.retrieve(QueryBundle(query_str=query))
        hits: list[Hit] = []
        for i, node in enumerate(nodes[:top_n]):
            hits.append(Hit(
                doc_id=str(node.metadata.get("chunk_id", node.id_)),
                rank=i + 1,
                score=node.score or 0.0,
            ))
        return hits

    @property
    def is_ready(self) -> bool:
        return self._bm25.is_ready or self._vector_available

    @property
    def strategy(self) -> str:
        return self._strategy
