"""专家团知识源注入 — 专家绑定文档/URL，执行时自动注入 context

核心思想：
  专家可绑定知识源（文档/URL/文本），执行时自动检索相关知识注入 prompt。
  使用 Qdrant expert_knowledge collection 存储。
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)

KNOWLEDGE_COLLECTION = "expert_knowledge"


class KnowledgeChunk(BaseModel):
    """知识片段"""
    content: str = Field(..., description="知识内容")
    source: str = Field(default="", description="来源")
    relevance: float = Field(default=0.0, description="相关度")


async def inject_expert_knowledge(
    db,
    expert_id: int,
    subtask: str,
    embedding_model: str = "text-embedding-3-small",
    top_k: int = 3,
) -> str:
    """从 expert_knowledge collection 检索相关知识

    Args:
        expert_id: 专家 ID
        subtask: 子任务（用于语义匹配）
        embedding_model: embedding 模型
        top_k: 返回 top-k 结果

    Returns:
        格式化的知识文本，无知识时返回空字符串
    """
    try:
        from app.mappers.qdrant_mapper import QdrantMapper
        from app.core.embeddings import get_embeddings

        qdrant = QdrantMapper()

        # 检查 collection 是否存在
        info = qdrant.collection_info(KNOWLEDGE_COLLECTION)
        if not info:
            qdrant.ensure_collection(KNOWLEDGE_COLLECTION)
            qdrant.ensure_payload_index(KNOWLEDGE_COLLECTION, "expert_id", "keyword")
            return ""
        if info.get("points_count", 0) == 0:
            return ""

        # 生成查询向量
        embeddings = get_embeddings()
        query_vector = await embeddings.aembed_query(subtask)

        # 检索（过滤 expert_id）
        results = qdrant.search(
            collection=KNOWLEDGE_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=0.3,
            filter_payload={"expert_id": str(expert_id)},
        )

        if not results:
            return ""

        # 格式化
        chunks = []
        for r in results:
            payload = r.payload or {}
            content = payload.get("content", "")
            source = payload.get("source", "")
            if content:
                prefix = f"[{source}] " if source else ""
                chunks.append(f"{prefix}{content}")

        if not chunks:
            return ""

        return "\n\n## 参考知识\n" + "\n---\n".join(chunks)

    except Exception as e:
        logger.warning(f"知识检索失败（降级为无知识执行）: {e}")
        return ""
