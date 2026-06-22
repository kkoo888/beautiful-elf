"""RAG 管道 — v4.0 Hybrid RAG（BM25 + 向量 + RRF + Rerank + Budget）

v4.0 重构（2026-06-14）:
  - 混合检索: BM25 (SQLite FTS5) + 向量检索 → RRF 融合
  - 去掉 Synthesizer: 检索结果直接拼入 prompt，由主 LLM 生成答案
  - Context Budget: 动态裁剪检索结果，防止 context overflow
  - Injection Guard: 所有检索结果用 <untrusted> 标签包裹
  - Workflow 编排: HybridRetrieve → Rerank → Budget → Wrap → Assemble

v3.0: QueryPipeline → Workflow 迁移
v2.0: Harrison Chase 视角优化

职责:
  - 文档解析（PDF / DOCX / PPTX / XLSX / CSV / JSON / HTML / MD / TXT）
  - 分块（SentenceSplitter）
  - Embedding + 存入 Qdrant
  - 混合检索 + 重排序 + 预算裁剪 + 注入防御（Workflow 编排）
"""
import asyncio
from pathlib import Path
from typing import List

from app.core.logging import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "knowledge_chunks"


# ── RAG Workflow（v4.0 Hybrid）────────────────────────────

def _build_rag_workflow(hybrid_retriever, reranker=None, budget_governor=None):
    """构建 v4.0 RAG Workflow: HybridRetrieve → Rerank → Budget → Assemble

    去掉 Synthesizer，检索结果直接拼入 prompt。
    """
    try:
        from llama_index.core.workflow import (
            Workflow, step, StartEvent, StopEvent, Context, Event,
        )
        from llama_index.core.schema import QueryBundle
    except ImportError:
        logger.warning("LlamaIndex Workflow 不可用")
        return None

    _hybrid = hybrid_retriever
    _reranker = reranker
    _budget = budget_governor

    # ── 定义事件类型 ──
    class HybridRetrieveEvent(Event):
        query_str: str
        doc_ids: list         # RRF 融合后的 doc_id 列表

    class RerankEvent(Event):
        query_str: str
        nodes: list           # rerank 后的节点

    class RAGWorkflow(Workflow):
        """HybridRetrieve → Rerank → Budget → Assemble"""

        @step()
        async def hybrid_retrieve(self, ctx: Context, ev: StartEvent) -> HybridRetrieveEvent:
            """混合检索: BM25 + 向量 → RRF 融合"""
            query_str = ev.get("query_str", "")
            hits = await asyncio.to_thread(_hybrid.retrieve, query_str, top_k=_hybrid._final_top_k)
            doc_ids = [h.doc_id for h in hits]
            return HybridRetrieveEvent(query_str=query_str, doc_ids=doc_ids)

        @step()
        async def rerank(self, ctx: Context, ev: HybridRetrieveEvent) -> RerankEvent:
            """Cross-Encoder 重排序"""
            query_str = ev.query_str
            doc_ids = ev.doc_ids

            # 从向量存储中取回节点文本
            nodes = await asyncio.to_thread(
                _resolve_nodes, _hybrid, query_str, doc_ids
            )

            if _reranker and nodes:
                query_bundle = QueryBundle(query_str=query_str)
                nodes = await asyncio.to_thread(
                    _reranker.postprocess_nodes, nodes, query_bundle
                )

            return RerankEvent(query_str=query_str, nodes=nodes[:_reranker.top_n if _reranker else 5])

        @step()
        async def assemble(self, ctx: Context, ev: RerankEvent) -> StopEvent:
            """Budget 裁剪 + Injection Guard + 直接拼装"""
            from app.agent.injection_guard import wrap_untrusted

            nodes = ev.nodes
            if not nodes:
                return StopEvent(result="")

            # ── Budget 裁剪 ──
            max_chars = _budget.snapshot().max_rag_result_chars if _budget else 6000
            total_chars = 0
            budgeted_nodes = []
            for node in nodes:
                node_chars = len(node.text)
                if total_chars + node_chars > max_chars:
                    # 截断最后一个节点
                    remaining = max_chars - total_chars
                    if remaining > 200:  # 至少保留 200 字符
                        budgeted_nodes.append(node)
                    break
                budgeted_nodes.append(node)
                total_chars += node_chars

            # ── Injection Guard + 拼装 ──
            parts = []
            for node in budgeted_nodes:
                score = node.score or 0
                filename = node.metadata.get("filename", "未知")
                source = f"rag:file={filename},score={score:.2f}"
                wrapped = wrap_untrusted(node.text, source=source)
                parts.append(wrapped)

            context_text = "\n\n---\n\n".join(parts)
            logger.info(
                f"[rag] 检索完成: {len(budgeted_nodes)}/{len(nodes)} 个节点, "
                f"{len(context_text)} chars (budget={max_chars})"
            )
            return StopEvent(result=context_text)

    return RAGWorkflow(timeout=30, verbose=False)


def _resolve_nodes(hybrid_retriever, query_str: str, doc_ids: list):
    """用原始查询取回 LlamaIndex Node（用于 reranking）"""
    try:
        vector_retriever = hybrid_retriever._vector_retriever
        if vector_retriever is None:
            return []
        from llama_index.core.schema import QueryBundle
        nodes = vector_retriever.retrieve(QueryBundle(query_str=query_str))
        # 按 doc_ids 过滤（只保留 RRF 融合命中的）
        id_set = set(doc_ids)
        return [n for n in nodes if str(n.metadata.get("chunk_id", n.id_)) in id_set]
    except Exception:
        return []


# ── RAG Pipeline ─────────────────────────────────────────

class RAGPipeline:
    """v4.0 Hybrid RAG Pipeline

    架构: Hybrid(BM25+Vector+RRF) → Rerank → Budget → Wrap → 直接拼prompt
    """

    def __init__(self, embedding_model, llm_model=None):
        self._embed_model = embedding_model
        self._llm = llm_model
        self._index = None
        self._retriever = None
        self._reranker = None
        self._node_parser = None
        self._workflow = None
        self._initialized = False

        # v4.0 新增组件
        from app.agent.hybrid_retriever import HybridRetriever
        from app.agent.context_budget import ContextBudgetGovernor

        self._hybrid_retriever = HybridRetriever(strategy="hybrid")
        self._budget = ContextBudgetGovernor(
            context_window_tokens=1_000_000,
            max_output_tokens=4096,
        )

    def apply_rag_config(self, config: dict):
        """从 DB rag_config 表读取参数，覆盖默认值

        Args:
            config: rag_config 表的 dict（snake_case keys）
        """
        chunk_size = config.get("chunk_size", 2048)
        chunk_overlap = config.get("chunk_overlap", 256)
        similarity_top_k = config.get("similarity_top_k", 10)
        bm25_top_n = config.get("bm25_top_n", 20)
        rrf_k = config.get("rrf_k", 60)
        rerank_top_n = config.get("rerank_top_n", 5)

        # 更新分块参数
        if self._node_parser:
            from llama_index.core.node_parser import SentenceSplitter
            self._node_parser = SentenceSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

        # 更新向量检索 top_k
        if self._retriever:
            self._retriever._similarity_top_k = similarity_top_k

        # 更新 HybridRetriever
        self._hybrid_retriever._lex_top_n = bm25_top_n
        self._hybrid_retriever._sem_top_n = bm25_top_n
        self._hybrid_retriever._rrf_k = rrf_k
        self._hybrid_retriever._final_top_k = max(bm25_top_n, similarity_top_k)

        # 更新 reranker top_n
        if self._reranker and hasattr(self._reranker, 'top_n'):
            self._reranker.top_n = rerank_top_n

        logger.info(
            f"[rag_pipeline] 配置已更新: chunk={chunk_size}/{chunk_overlap}, "
            f"top_k={similarity_top_k}, bm25={bm25_top_n}, rrf_k={rrf_k}, rerank_n={rerank_top_n}"
        )

    async def initialize(self):
        """初始化索引、检索器和 Workflow"""
        if self._initialized:
            return

        try:
            from llama_index.core import VectorStoreIndex, StorageContext
            from llama_index.vector_stores.qdrant import QdrantVectorStore
            from llama_index.core.node_parser import SentenceSplitter

            from app.core.qdrant_client import get_qdrant
            client = get_qdrant()

            vector_store = QdrantVectorStore(
                client=client,
                collection_name=COLLECTION_NAME,
            )

            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            self._index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=self._embed_model,
                storage_context=storage_context,
            )

            self._node_parser = SentenceSplitter(
                chunk_size=2048,
                chunk_overlap=256,
            )

            self._retriever = self._index.as_retriever(similarity_top_k=10)

            # 设置向量检索器到 HybridRetriever
            self._hybrid_retriever.set_vector_retriever(self._retriever)

            # 构建 Workflow
            self._build_workflow()

            self._initialized = True
            logger.info("RAG 管道初始化完成（Hybrid v4.0）")

        except ImportError as e:
            logger.warning(f"缺少 LlamaIndex 依赖: {e}")
            raise
        except Exception as e:
            logger.error(f"RAG 管道初始化失败: {e}", exc_info=True)
            raise

    def _build_workflow(self):
        """构建 v4.0 RAG Workflow"""
        self._workflow = _build_rag_workflow(
            hybrid_retriever=self._hybrid_retriever,
            reranker=self._reranker,
            budget_governor=self._budget,
        )

        if self._workflow:
            logger.info("RAG Workflow v4.0 构建完成")
        else:
            logger.info("Workflow 不可用，使用手动检索模式")

    def init_reranker(self):
        """启动时调用一次，加载重排序模型"""
        try:
            from llama_index.core.postprocessor import SentenceTransformerRerank
            self._reranker = SentenceTransformerRerank(
                model="BAAI/bge-reranker-v2-m3",
                top_n=5,
            )
            logger.info("重排序模型加载成功: BAAI/bge-reranker-v2-m3")

            if self._initialized:
                self._build_workflow()

        except Exception as e:
            logger.warning(f"重排序模型加载失败，降级为不重排: {e}")
            self._reranker = None

    def index_bm25(self, chunks: list[dict]):
        """构建 BM25 索引（文档入库后调用）"""
        self._hybrid_retriever.index(chunks)

    def add_bm25_chunks(self, chunks: list[dict]):
        """增量添加 BM25 分块"""
        self._hybrid_retriever.add_chunks(chunks)

    def remove_bm25_doc(self, doc_id: str):
        """删除文档的 BM25 索引"""
        self._hybrid_retriever.remove_by_doc_id(doc_id)

    def update_budget(self, context_window_tokens: int, max_output_tokens: int = 4096):
        """动态更新 context budget（模型切换时）"""
        self._budget.update_window(context_window_tokens, max_output_tokens)

    @property
    def is_ready(self) -> bool:
        return self._initialized

    # ── 文档入库 ──────────────────────────────────────────

    async def ingest_document(self, file_path: str, filename: str, doc_id: int) -> dict:
        """文档入库：解析 → 分块 → Embedding → Qdrant + BM25 双写"""
        if not self._initialized:
            await self.initialize()

        def _ingest():
            from llama_index.core import SimpleDirectoryReader

            reader = SimpleDirectoryReader(input_files=[file_path])
            documents = reader.load_data()

            for doc in documents:
                doc.metadata.update({
                    "document_id": doc_id,
                    "filename": filename,
                    "file_type": Path(file_path).suffix.lstrip("."),
                })

            nodes = self._node_parser.get_nodes_from_documents(documents)
            self._index.insert_nodes(nodes)

            # ── 同步写入 BM25 索引 ──
            bm25_chunks = []
            for node in nodes:
                bm25_chunks.append({
                    "chunk_id": node.id_,
                    "filename": filename,
                    "content": node.text,
                    "document_id": doc_id,
                })
            self._hybrid_retriever.add_chunks(bm25_chunks)

            return len(nodes)

        chunk_count = await asyncio.to_thread(_ingest)
        logger.info(f"文档入库完成: {filename}, {chunk_count} 个分块（向量+BM25 双写）")
        return {"document_id": doc_id, "chunks": chunk_count}

    # ── 检索（v4.0: Workflow 优先，手动降级）──────────────

    async def search(self, query: str, limit: int = 5) -> str:
        """检索链路：Hybrid → Rerank → Budget → Wrap → 拼装上下文

        v4.0: 优先使用 Workflow 编排，不可用时降级为手动调用。
        """
        if not self._initialized:
            return ""

        # ── 优先: Workflow ──
        if self._workflow:
            try:
                result = await self._workflow.run(query_str=query)
                response_text = str(result) if result else ""
                if response_text:
                    logger.info(f"[rag] Workflow 检索完成: {len(response_text)} chars")
                    return response_text
            except Exception as e:
                logger.warning(f"[rag] Workflow 执行失败，降级为手动: {e}")

        # ── 降级: 手动调用 ──
        return await self._manual_search(query, limit)

    async def _manual_search(self, query: str, limit: int = 5) -> str:
        """手动检索（Workflow 不可用时的降级方案）

        v4.0: Hybrid(BM25+Vector+RRF) → Resolve Nodes → Rerank → Budget → Wrap
        """
        from app.agent.injection_guard import wrap_untrusted
        from llama_index.core.schema import QueryBundle

        # ── 混合检索（BM25 + 向量 → RRF 融合）──
        hits = await asyncio.to_thread(
            self._hybrid_retriever.retrieve, query, top_k=self._hybrid_retriever._final_top_k
        )

        if not hits:
            return ""

        doc_ids = [h.doc_id for h in hits]

        # ── 取回节点（用原始查询 + doc_ids 过滤）──
        nodes = await asyncio.to_thread(
            _resolve_nodes, self._hybrid_retriever, query, doc_ids
        )

        if not nodes:
            return ""

        # ── Reranking ──
        if self._reranker:
            query_bundle = QueryBundle(query_str=query)
            nodes = await asyncio.to_thread(
                self._reranker.postprocess_nodes, nodes, query_bundle
            )

        nodes = nodes[:limit]

        # ── Budget 裁剪 ──
        max_chars = self._budget.snapshot().max_rag_result_chars
        total_chars = 0
        budgeted_nodes = []
        for node in nodes:
            if total_chars + len(node.text) > max_chars:
                break
            budgeted_nodes.append(node)
            total_chars += len(node.text)

        # ── Injection Guard + 拼装 ──
        parts = []
        for node in budgeted_nodes:
            score = node.score or 0
            filename = node.metadata.get("filename", "未知")
            source = f"rag:file={filename},score={score:.2f}"
            wrapped = wrap_untrusted(node.text, source=source)
            parts.append(wrapped)

        return "\n\n---\n\n".join(parts)

    async def search_with_scores(self, query: str, limit: int = 5) -> List[dict]:
        """检索并返回带分数的结果列表"""
        if not self._initialized:
            return []

        from llama_index.core.schema import QueryBundle

        nodes = await asyncio.to_thread(self._retriever.retrieve, query)

        if self._reranker:
            query_bundle = QueryBundle(query_str=query)
            nodes = await asyncio.to_thread(
                self._reranker.postprocess_nodes, nodes, query_bundle
            )

        nodes = nodes[:limit]

        return [
            {
                "content": node.text,
                "score": node.score or 0,
                "filename": node.metadata.get("filename", "未知"),
                "document_id": node.metadata.get("document_id", 0),
            }
            for node in nodes
        ]

    # ── 评估 ─────────────────────────────────────────────

    async def evaluate_retrieval(self, query: str, expected_docs: List[int] = None) -> dict:
        """评估检索质量"""
        if not self._initialized:
            return {"mrr": 0, "hit_rate": 0, "retrieved_docs": 0}

        try:
            from llama_index.core.evaluation import RetrieverEvaluator

            evaluator = RetrieverEvaluator.from_metric_names(
                ["mrr", "hit_rate"],
                retriever=self._retriever,
            )

            result = await asyncio.to_thread(
                evaluator.evaluate,
                query=query,
                expected_ids=[str(d) for d in (expected_docs or [])],
            )

            return {
                "mrr": result.metric_dict.get("mrr", {}).get("score", 0),
                "hit_rate": result.metric_dict.get("hit_rate", {}).get("score", 0),
                "retrieved_docs": len(result.retrieved_ids),
            }
        except Exception as e:
            logger.warning(f"检索评估失败: {e}")
            return {"mrr": 0, "hit_rate": 0, "retrieved_docs": 0}

    # ── 删除 ─────────────────────────────────────────────

    async def delete_by_document(self, doc_id: int) -> bool:
        """删除文档关联的所有向量 + BM25 索引"""
        if not self._initialized:
            return False

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            client = self._index.vector_store._client
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.document_id",
                            match=MatchValue(value=doc_id),
                        )
                    ]
                ),
            )

            # 同步删除 BM25 索引
            self._hybrid_retriever.remove_by_doc_id(str(doc_id))

            logger.info(f"已删除文档 {doc_id} 的向量 + BM25 索引")
            return True
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False
