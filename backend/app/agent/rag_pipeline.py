"""RAG 管道 — LlamaIndex 驱动，Qdrant 存储

职责:
  - 文档解析（PDF / DOCX / TXT / MD）
  - 分块（SentenceSplitter）
  - Embedding + 存入 Qdrant
  - 混合检索 + 重排序

注意:
  - 本模块是 Agent 引擎的子系统，由 knowledge_service 调用
  - 不含路由细节，不含业务编排（由 service 层处理）
"""
import uuid
from pathlib import Path
from typing import List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "knowledge_chunks"


class RAGPipeline:
    """LlamaIndex 驱动的 RAG 管道"""

    def __init__(self, qdrant_url: str, embedding_model, llm_model=None):
        """
        Args:
            qdrant_url: Qdrant 连接地址
            embedding_model: LlamaIndex 兼容的 Embedding 实例
            llm_model: LlamaIndex 兼容的 LLM 实例（用于查询改写，可选）
        """
        self._qdrant_url = qdrant_url
        self._embed_model = embedding_model
        self._llm = llm_model
        self._index = None
        self._retriever = None
        self._reranker = None
        self._node_parser = None
        self._initialized = False

    async def initialize(self):
        """初始化索引和检索器（需要在异步上下文中调用）"""
        if self._initialized:
            return

        try:
            import qdrant_client
            from llama_index.core import VectorStoreIndex, StorageContext
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

            self._initialized = True
            logger.info("RAG 管道初始化完成")

        except ImportError as e:
            logger.warning(f"缺少 LlamaIndex 依赖，RAG 管道不可用: {e}")
            raise
        except Exception as e:
            logger.error(f"RAG 管道初始化失败: {e}", exc_info=True)
            raise

    def init_reranker(self):
        """启动时调用一次，加载重排序模型"""
        try:
            from llama_index.core.postprocessor import SentenceTransformerRerank
            self._reranker = SentenceTransformerRerank(
                model="BAAI/bge-reranker-v2-m3",
                top_n=5,
            )
            logger.info("重排序模型加载成功")
        except Exception as e:
            logger.warning(f"重排序模型加载失败，降级为不重排: {e}")
            self._reranker = None

    @property
    def is_ready(self) -> bool:
        return self._initialized

    # ── 文档入库 ──────────────────────────────────────────

    async def ingest_document(self, file_path: str, filename: str, doc_id: int) -> dict:
        """
        文档入库：解析 → 分块 → Embedding → Qdrant 存储。

        Args:
            file_path: 文件本地路径
            filename: 原始文件名
            doc_id: MySQL knowledge_document.id

        Returns:
            {"document_id": int, "chunks": int}
        """
        if not self._initialized:
            await self.initialize()

        import asyncio

        def _ingest():
            from llama_index.core import SimpleDirectoryReader

            # 1. 加载文档
            reader = SimpleDirectoryReader(input_files=[file_path])
            documents = reader.load_data()

            # 2. 附加元数据
            for doc in documents:
                doc.metadata.update({
                    "document_id": doc_id,
                    "filename": filename,
                    "file_type": Path(file_path).suffix.lstrip("."),
                })

            # 3. 分块
            nodes = self._node_parser.get_nodes_from_documents(documents)

            # 4. 存入 Qdrant（LlamaIndex 内部处理 Embedding）
            self._index.insert_nodes(nodes)

            return len(nodes)

        chunk_count = await asyncio.to_thread(_ingest)
        logger.info(f"文档入库完成: {filename}, {chunk_count} 个分块")
        return {"document_id": doc_id, "chunks": chunk_count}

    # ── 检索 ─────────────────────────────────────────────

    async def search(self, query: str, limit: int = 5) -> str:
        """
        检索链路：向量检索 → 重排序 → 拼装上下文。

        Args:
            query: 查询文本
            limit: 返回结果数

        Returns:
            拼装后的上下文字符串
        """
        if not self._initialized:
            return ""

        import asyncio
        from llama_index.core.schema import QueryBundle

        # 1. 向量检索
        nodes = await asyncio.to_thread(self._retriever.retrieve, query)

        # 2. 重排序
        if self._reranker:
            query_bundle = QueryBundle(query_str=query)
            nodes = self._reranker.postprocess_nodes(nodes, query_bundle=query_bundle)

        # 3. Top K
        nodes = nodes[:limit]

        if not nodes:
            return ""

        # 4. 拼装上下文
        context_parts = []
        for node in nodes:
            score = node.score or 0
            filename = node.metadata.get("filename", "未知")
            context_parts.append(f"[来源: {filename} | 相关度: {score:.2f}]\n{node.text}")

        return "\n\n---\n\n".join(context_parts)

    async def search_with_scores(self, query: str, limit: int = 5) -> List[dict]:
        """
        检索并返回带分数的结果列表。

        Args:
            query: 查询文本
            limit: 返回结果数

        Returns:
            [{"content": str, "score": float, "filename": str, "document_id": int}]
        """
        if not self._initialized:
            return []

        import asyncio
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
