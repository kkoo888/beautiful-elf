"""Qdrant Mapper - 封装向量操作"""
from typing import Optional, List
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)

from app.core.qdrant_client import get_qdrant
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    id: str
    score: float
    payload: dict


class QdrantMapper:
    """封装 Qdrant 向量操作"""

    def __init__(self):
        self._client: QdrantClient = get_qdrant()

    def ensure_collection(self, name: str, vector_size: int = 1024) -> None:
        """确保集合存在"""
        try:
            collections = [c.name for c in self._client.get_collections().collections]
            if name not in collections:
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=vector_size, distance=Distance.COSINE
                    ),
                )
                logger.info(f"创建 Qdrant 集合: {name}")
        except Exception as e:
            logger.error(f"确保集合失败: {name}, error={e}")
            raise

    def upsert(
        self,
        collection: str,
        point_id: str,
        vector: List[float],
        payload: dict = None,
    ) -> None:
        """插入或更新向量"""
        try:
            self._client.upsert(
                collection_name=collection,
                points=[
                    PointStruct(id=point_id, vector=vector, payload=payload or {})
                ],
            )
        except Exception as e:
            logger.error(f"Qdrant upsert 失败: {collection}/{point_id}, error={e}")
            raise

    def search(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_payload: dict = None,
    ) -> List[SearchResult]:
        """向量搜索"""
        try:
            query_filter = None
            if filter_payload:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key=k, match=MatchValue(value=v)
                        )
                        for k, v in filter_payload.items()
                    ]
                )

            # qdrant_client >= 1.7 用 query_points，旧版用 search
            if hasattr(self._client, "query_points"):
                results = self._client.query_points(
                    collection_name=collection,
                    query=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=query_filter,
                ).points
            else:
                results = self._client.search(
                    collection_name=collection,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=query_filter,
                )

            return [
                SearchResult(
                    id=str(r.id), score=r.score, payload=r.payload or {}
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search 失败: {collection}, error={e}")
            return []

    def get_by_id(
        self, collection: str, point_id: str
    ) -> Optional[dict]:
        """按 ID 获取向量"""
        try:
            results = self._client.retrieve(
                collection_name=collection, ids=[point_id]
            )
            if results:
                return results[0].payload
            return None
        except Exception as e:
            logger.error(f"Qdrant get_by_id 失败: {collection}/{point_id}, error={e}")
            return None

    def delete_by_filter(self, collection: str, filter_payload: dict) -> None:
        """按条件删除"""
        try:
            self._client.delete(
                collection_name=collection,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key=k, match=MatchValue(value=v)
                        )
                        for k, v in filter_payload.items()
                    ]
                ),
            )
        except Exception as e:
            logger.error(f"Qdrant delete 失败: {collection}, error={e}")

    def count(self, collection: str, filter_payload: dict = None) -> int:
        """统计向量数量"""
        try:
            result = self._client.count(
                collection_name=collection,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key=k, match=MatchValue(value=v)
                        )
                        for k, v in filter_payload.items()
                    ]
                )
                if filter_payload
                else None,
            )
            return result.count
        except Exception as e:
            logger.error(f"Qdrant count 失败: {collection}, error={e}")
            return 0
