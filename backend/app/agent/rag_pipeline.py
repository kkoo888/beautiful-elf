"""RAG 管道 — LlamaIndex Workflow 规范化（v3.0）

v3.0 重构:
  - 移除已废弃的 QueryPipeline，改用 LlamaIndex Workflow（事件驱动编排）
  - 检索链路: retrieve → rerank → synthesize，通过 @step 声明式组装
  - 保留手动检索作为高性能降级方案
  - 响应合成: get_response_synthesizer 替代直接实例化 CompactAndRefine

v2.0 重构（Harrison Chase 视角优化）:
  - 重排序: SentenceTransformerRerank 作为 postprocessor 节点
  - 评估: 内置 FaithfulnessEvaluator / RelevancyEvaluator

职责:
  - 文档解析（PDF / DOCX / PPTX / XLSX / CSV / JSON / HTML / MD / TXT / EPUB / IPYNB）
  - 分块（SentenceSplitter）
  - Embedding + 存入 Qdrant
  - 混合检索 + 重排序（Workflow 编排）

注意:
  - 本模块是 Agent 引擎的子系统，由 knowledge_service 调用
  - 不含路由细节，不含业务编排（由 service 层处理）
"""
import uuid
import asyncio
from pathlib import Path
from typing import List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "knowledge_chunks"


# ── RAG Workflow（LlamaIndex Workflow 编排）────────────────

def _build_rag_workflow(retriever, reranker=None, response_synthesizer=None):
    """构建 RAG Workflow：retrieve → rerank → synthesize

    使用 LlamaIndex Workflow 的 @step 事件驱动编排，
    替代已废弃的 QueryPipeline DAG。
    """
    try:
        from llama_index.core.workflow import (
            Workflow, step, StartEvent, StopEvent, Context,
        )
        from llama_index.core.schema import QueryBundle
    except ImportError:
        logger.warning("LlamaIndex Workflow 不可用（llama-index 版本过旧）")
        return None

    _retriever = retriever
    _reranker = reranker
    _synthesizer = response_synthesizer

    class RAGWorkflow(Workflow):
        """retrieve → rerank → synthesize 工作流"""

        @step()
        async def retrieve(self, ctx: Context, ev: StartEvent) -> "RerankEvent":
            query_str = ev.get("query_str", "")
            nodes = await asyncio.to_thread(_retriever.retrieve, query_str)
            return RerankEvent(query_str=query_str, nodes=nodes)

        @step()
        async def rerank(self, ctx: Context, ev: "RerankEvent") -> "SynthesizeEvent":
            nodes = ev.nodes
            if _reranker:
                query_bundle = QueryBundle(query_str=ev.query_str)
                nodes = _reranker.postprocess_nodes(nodes, query_bundle=query_bundle)
            return SynthesizeEvent(query_str=ev.query_str, nodes=nodes)

        @step()
        async def synthesize(self, ctx: Context, ev: "SynthesizeEvent") -> StopEvent:
            if _synthesizer:
                from llama_index.core.schema import QueryBundle
                query_bundle = QueryBundle(query_str=ev.query_str)
                response = await asyncio.to_thread(
                    _synthesizer.synthesize, query_bundle, ev.nodes
                )
                return StopEvent(result=str(response))
            else:
                # 无 synthesizer 时直接拼接文本
                parts = []
                for node in ev.nodes[:5]:
                    score = node.score or 0
                    fname = node.metadata.get("filename", "未知")
                    parts.append(f"[来源: {fname} | 相关度: {score:.2f}]\n{node.text}")
                return StopEvent(result="\n\n---\n\n".join(parts))

    # 定义中间事件类型
    from llama_index.core.workflow import Event

    class RerankEvent(Event):
        query_str: str
        nodes: list

    class SynthesizeEvent(Event):
        query_str: str
        nodes: list

    return RAGWorkflow(timeout=30, verbose=False)


# ── RAG Pipeline ─────────────────────────────────────────

class RAGPipeline:
    """LlamaIndex Workflow 驱动的 RAG 管道（v3.0）"""

    def __init__(self, qdrant_url: str, embedding_model, llm_model=None):
        self._qdrant_url = qdrant_url
        self._embed_model = embedding_model
        self._llm = llm_model
        self._index = None
        self._retriever = None
        self._reranker = None
        self._node_parser = None
        self._synthesizer = None
        self._workflow = None
        self._initialized = False

    async def initialize(self):
        """初始化索引、检索器和 Workflow"""
        if self._initialized:
            return

        try:
            import qdrant_client
            from llama_index.core import VectorStoreIndex, StorageContext, Settings
            from llama_index.vector_stores.qdrant import QdrantVectorStore
            from llama_index.core.node_parser import SentenceSplitter

            client = qdrant_client.QdrantClient(url=self._qdrant_url)

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
                chunk_size=512,
                chunk_overlap=64,
            )

            self._retriever = self._index.as_retriever(similarity_top_k=10)

            # ── 构建 Workflow ──────────────────────
            self._build_workflow()

            self._initialized = True
            logger.info("RAG 管道初始化完成（Workflow v3.0）")

        except ImportError as e:
            logger.warning(f"缺少 LlamaIndex 依赖，RAG 管道不可用: {e}")
            raise
        except Exception as e:
            logger.error(f"RAG 管道初始化失败: {e}", exc_info=True)
            raise

    def _build_workflow(self):
        """构建 RAG Workflow（retrieve → rerank → synthesize）"""
        try:
            from llama_index.core.response_synthesizers import get_response_synthesizer
            self._synthesizer = get_response_synthesizer(response_mode="compact")
        except ImportError:
            logger.warning("get_response_synthesizer 不可用，合成将使用文本拼接")
            self._synthesizer = None

        self._workflow = _build_rag_workflow(
            retriever=self._retriever,
            reranker=self._reranker,
            response_synthesizer=self._synthesizer,
        )

        if self._workflow:
            logger.info("RAG Workflow 构建完成")
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
            logger.info("重排序模型加载成功")

            # 重建 Workflow（加入 reranker）
            if self._initialized:
                self._build_workflow()

        except Exception as e:
            logger.warning(f"重排序模型加载失败，降级为不重排: {e}")
            self._reranker = None

    @property
    def is_ready(self) -> bool:
        return self._initialized

    # ── 文档入库 ──────────────────────────────────────────

    async def ingest_document(self, file_path: str, filename: str, doc_id: int) -> dict:
        """文档入库：解析 → 分块 → Embedding → Qdrant 存储"""
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
            return len(nodes)

        chunk_count = await asyncio.to_thread(_ingest)
        logger.info(f"文档入库完成: {filename}, {chunk_count} 个分块")
        return {"document_id": doc_id, "chunks": chunk_count}

    # ── 检索（v3.0: Workflow 优先，手动降级）──────────────

    async def search(self, query: str, limit: int = 5) -> str:
        """检索链路：Workflow → 拼装上下文。

        v3.0: 优先使用 Workflow 编排，不可用时降级为手动调用。
        """
        if not self._initialized:
            return ""

        # ── 优先: Workflow ─────────────────────────
        if self._workflow:
            try:
                result = await self._workflow.run(query_str=query)
                response_text = str(result) if result else ""
                if response_text:
                    logger.info(f"[rag] Workflow 检索完成: {len(response_text)} chars")
                    return response_text[:6000]
            except Exception as e:
                logger.warning(f"[rag] Workflow 执行失败，降级为手动: {e}")

        # ── 降级: 手动调用 ──────────────────────────
        return await self._manual_search(query, limit)

    async def _manual_search(self, query: str, limit: int = 5) -> str:
        """手动检索（Workflow 不可用时的降级方案）"""
        from llama_index.core.schema import QueryBundle

        nodes = await asyncio.to_thread(self._retriever.retrieve, query)

        if self._reranker:
            query_bundle = QueryBundle(query_str=query)
            nodes = self._reranker.postprocess_nodes(nodes, query_bundle=query_bundle)

        nodes = nodes[:limit]

        if not nodes:
            return ""

        context_parts = []
        for node in nodes:
            score = node.score or 0
            filename = node.metadata.get("filename", "未知")
            context_parts.append(f"[来源: {filename} | 相关度: {score:.2f}]\n{node.text}")

        return "\n\n---\n\n".join(context_parts)

    async def search_with_scores(self, query: str, limit: int = 5) -> List[dict]:
        """检索并返回带分数的结果列表"""
        if not self._initialized:
            return []

        from llama_index.core.schema import QueryBundle

        nodes = await asyncio.to_thread(self._retriever.retrieve, query)

        if self._reranker:
            query_bundle = QueryBundle(query_str=query)
            nodes = self._reranker.postprocess_nodes(nodes, query_bundle=query_bundle)

        nodes = nodes[:limit]

        results = []
        for node in nodes:
            results.append({
                "content": node.text,
                "score": node.score or 0,
                "filename": node.metadata.get("filename", "未知"),
                "document_id": node.metadata.get("document_id", 0),
            })

        return results

    # ── 评估 ─────────────────────────────────────────────

    async def evaluate_retrieval(self, query: str, expected_docs: List[int] = None) -> dict:
        """评估检索质量（LlamaIndex RetrieverEvaluator）

        Returns: {"mrr": float, "hit_rate": float, "retrieved_docs": int}
        """
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
        """删除文档关联的所有向量"""
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
            logger.info(f"已删除文档 {doc_id} 的向量")
            return True
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False
