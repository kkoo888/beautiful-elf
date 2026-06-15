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
    MatchText,
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

    def ensure_payload_index(self, collection: str, field_name: str, field_type: str = "text") -> None:
        """确保 payload 字段有索引（支持全文检索等）"""
        try:
            from qdrant_client.models import PayloadSchemaType
            type_map = {
                "text": PayloadSchemaType.TEXT,
                "keyword": PayloadSchemaType.KEYWORD,
                "integer": PayloadSchemaType.INTEGER,
                "float": PayloadSchemaType.FLOAT,
                "bool": PayloadSchemaType.BOOL,
            }
            schema_type = type_map.get(field_type, PayloadSchemaType.TEXT)
            self._client.create_payload_index(
                collection_name=collection,
                field_name=field_name,
                field_schema=schema_type,
            )
            logger.info(f"创建 payload 索引: {collection}.{field_name} ({field_type})")
        except Exception as e:
            # 索引已存在时会抛异常，忽略即可
            if "already exists" not in str(e).lower():
                logger.warning(f"创建 payload 索引失败（非致命）: {collection}.{field_name}: {e}")

    def search(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_payload: dict = None,
        extra_conditions: list = None,
        raw_filter: Filter = None,
    ) -> List[SearchResult]:
        """向量搜索

        Args:
            extra_conditions: 额外的 must 条件（如 MatchText 全文检索条件）
            raw_filter: 直接传入 Filter 对象（优先级高于 filter_payload + extra_conditions）
        """
        try:
            if raw_filter:
                query_filter = raw_filter
            else:
                must_conditions = []
                if filter_payload:
                    must_conditions.extend([
                        FieldCondition(key=k, match=MatchValue(value=v))
                        for k, v in filter_payload.items()
                    ])
                if extra_conditions:
                    must_conditions.extend(extra_conditions)
                query_filter = Filter(must=must_conditions) if must_conditions else None

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

    def scroll(
        self,
        collection: str,
        filter_payload: dict = None,
        limit: int = 100,
        offset: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """分页遍历向量（不返回向量本身，节省带宽）

        Returns:
            (points, next_offset) — points 为 list[{id, payload}]，next_offset 为 None 表示无更多数据
        """
        try:
            scroll_filter = None
            if filter_payload:
                scroll_filter = Filter(
                    must=[
                        FieldCondition(key=k, match=MatchValue(value=v))
                        for k, v in filter_payload.items()
                    ]
                )

            from qdrant_client.models import PointIdsList
            scroll_offset = None
            if offset:
                scroll_offset = offset

            points, next_offset = self._client.scroll(
                collection_name=collection,
                scroll_filter=scroll_filter,
                limit=limit,
                offset=scroll_offset,
                with_vectors=False,
            )

            result = [
                {"id": str(p.id), "payload": p.payload or {}}
                for p in points
            ]
            return result, str(next_offset) if next_offset is not None else None
        except Exception as e:
            logger.error(f"Qdrant scroll 失败: {collection}, error={e}")
            return [], None

    def collection_info(self, collection: str) -> dict | None:
        """获取集合元信息（points_count, status, vectors_count 等）

        Returns:
            {"name": str, "status": str, "points_count": int, "vectors_count": int}
            连接失败或集合不存在时返回 None
        """
        try:
            info = self._client.get_collection(collection_name=collection)
            return {
                "name": collection,
                "status": str(info.status),
                "points_count": info.points_count or 0,
                "vectors_count": info.vectors_count or 0,
            }
        except Exception as e:
            logger.warning(f"Qdrant collection_info 失败（集合可能不存在）: {collection}, error={e}")
            return None
