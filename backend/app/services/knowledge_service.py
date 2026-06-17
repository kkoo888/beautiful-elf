"""知识库 Service — 封装 RAG 管道的业务编排

职责:
  - 文档上传 → 保存元数据 → 触发异步入库
  - 文档列表 / 详情 / 删除
  - 语义搜索

遵循规范:
  - 分层架构: service 调用 repository，不含 SQL 细节
  - 统一异常: 使用 app.core.exceptions 中的异常类
  - ORM → Pydantic: 静态 _to_out 方法
"""
import os
import uuid
import shutil
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.knowledge_repo import KnowledgeDocumentRepo, KnowledgeChunkRepo
from app.schemas.knowledge import (
    KnowledgeDocumentOut,
    KnowledgeChunkOut,
    KnowledgeSearchResult,
    KnowledgeSearchResponse,
    QdrantCollectionStats,
    DocumentVectorCount,
    QdrantVectorRecord,
)
from app.mappers.qdrant_mapper import QdrantMapper
from app.core.exceptions import RecordNotFoundError, StorageError
from app.core.logging import get_logger

logger = get_logger(__name__)

# 上传文件临时存储目录
UPLOAD_DIR = "/tmp/beautiful-elf-uploads"

# Qdrant 集合名（与 rag_pipeline.py 保持一致）
COLLECTION_NAME = "knowledge_chunks"


class KnowledgeService:
    """知识库业务服务"""

    def __init__(self):
        self.doc_repo = KnowledgeDocumentRepo()
        self.chunk_repo = KnowledgeChunkRepo()
        self._rag_pipeline = None
        self._qdrant = QdrantMapper()

    @property
    def rag_pipeline(self):
        """延迟加载 RAG 管道"""
        return self._rag_pipeline

    def set_rag_pipeline(self, pipeline):
        """注入 RAG 管道实例（应用启动时调用）"""
        self._rag_pipeline = pipeline

    # ── 文档 CRUD ────────────────────────────────────────

    async def list_documents(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        status: Optional[int] = None, deleted_only: bool = False,
    ) -> Tuple[List[KnowledgeDocumentOut], int]:
        """获取文档列表"""
        offset = (page - 1) * page_size
        items = await self.doc_repo.find_all(
            db, offset=offset, limit=page_size, status=status, deleted_only=deleted_only,
        )
        total = await self.doc_repo.count(db, status=status, deleted_only=deleted_only)
        return [self._to_out(i) for i in items], total

    async def get_document(self, db: AsyncSession, doc_id: int) -> KnowledgeDocumentOut:
        """获取文档详情"""
        item = await self.doc_repo.find_by_id(db, doc_id)
        if not item:
            raise RecordNotFoundError("知识库文档不存在")
        return self._to_out(item)

    async def upload_document(
        self, db: AsyncSession, filename: str, file_type: str, file_size: int, file_content: bytes,
    ) -> KnowledgeDocumentOut:
        """
        上传文档：保存文件 → 创建 DB 记录 → 触发异步向量化。

        Args:
            db: 数据库会话
            filename: 原始文件名
            file_type: 文件类型 (pdf/docx/pptx/xlsx/csv/json/html/md/txt/epub/ipynb)
            file_size: 文件大小
            file_content: 文件内容（bytes）

        Returns:
            文档记录
        """
        # 1. 保存文件到临时目录
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        with open(file_path, "wb") as f:
            f.write(file_content)

        # 2. 创建 DB 记录（状态=待处理）
        doc = await self.doc_repo.create(db, {
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "chunk_count": 0,
            "status": 0,  # 待处理
        })

        # 3. 触发异步向量化（Celery 任务或后台线程）
        try:
            await self._process_document(db, doc.id, file_path, filename)
        except Exception as e:
            logger.error(f"文档向量化失败: {e}", exc_info=True)
            await self.doc_repo.set_status(db, doc.id, 3, str(e))

        return self._to_out(await self.doc_repo.find_by_id(db, doc.id))

    async def delete_document(self, db: AsyncSession, doc_id: int) -> bool:
        """删除文档：软删除 DB 记录 + 删除 Qdrant 向量"""
        item = await self.doc_repo.find_by_id(db, doc_id)
        if not item:
            raise RecordNotFoundError("知识库文档不存在")

        # 删除 Qdrant 向量
        if self._rag_pipeline and self._rag_pipeline.is_ready:
            try:
                await self._rag_pipeline.delete_by_document(doc_id)
            except Exception as e:
                logger.warning(f"删除向量失败（非致命）: {e}")

        # 删除 MySQL 分块记录
        await self.chunk_repo.delete_by_document(db, doc_id)

        # 软删除文档记录
        return await self.doc_repo.soft_delete(db, doc_id)

    async def list_chunks(self, db: AsyncSession, doc_id: int) -> list[KnowledgeChunkOut]:
        """获取文档的分块列表"""
        doc = await self.doc_repo.find_by_id(db, doc_id)
        if not doc:
            raise RecordNotFoundError("知识库文档不存在")
        items = await self.chunk_repo.find_by_document(db, doc_id)
        return [self._chunk_to_out(c) for c in items]

    async def restore_document(self, db: AsyncSession, doc_id: int) -> bool:
        """恢复被软删除的文档"""
        item = await self.doc_repo.find_by_id(db, doc_id)
        if not item:
            raise RecordNotFoundError("知识库文档不存在")
        return await self.doc_repo.restore(db, doc_id)

    # ── Qdrant 向量库管理 ────────────────────────────────

    def get_qdrant_stats(self) -> QdrantCollectionStats:
        """获取 Qdrant 集合状态（集合不存在则自动创建）"""
        try:
            info = self._qdrant.collection_info(COLLECTION_NAME)
        except Exception:
            info = None

        if info is None:
            # 集合不存在 → 懒创建
            try:
                self._qdrant.ensure_collection(COLLECTION_NAME, vector_size=1024)
                info = self._qdrant.collection_info(COLLECTION_NAME)
            except Exception as e:
                logger.error(f"Qdrant 连接失败: {e}")
                return QdrantCollectionStats(
                    collection_name=COLLECTION_NAME,
                    vector_count=0,
                    status="red",
                    is_connected=False,
                )

        status_str = str(info.get("status", "unknown")).lower()
        return QdrantCollectionStats(
            collection_name=info["name"],
            vector_count=info.get("points_count", 0),
            status=status_str,
            is_connected=True,
        )

    async def get_document_vector_summary(self, db: AsyncSession) -> list[DocumentVectorCount]:
        """按文档聚合 Qdrant 中的向量计数（同时从 MySQL 取文件名）"""
        points, _ = self._qdrant.scroll(COLLECTION_NAME, limit=10000)
        # 按 document_id 聚合
        counts: dict[int, int] = {}
        for p in points:
            doc_id = p.get("payload", {}).get("document_id")
            if doc_id is not None:
                counts[doc_id] = counts.get(doc_id, 0) + 1

        # 从 MySQL 取文件名
        result = []
        for doc_id, cnt in counts.items():
            doc = await self.doc_repo.find_by_id(db, int(doc_id))
            filename = doc.filename if doc else f"(ID={doc_id} 已删除)"
            result.append(DocumentVectorCount(
                document_id=int(doc_id), filename=filename, vector_count=cnt,
            ))

        result.sort(key=lambda x: x.vector_count, reverse=True)
        return result

    def list_vectors(
        self, document_id: int, offset: str | None = None, limit: int = 20,
    ) -> tuple[list[QdrantVectorRecord], str | None]:
        """列出指定文档的 Qdrant 向量"""
        points, next_offset = self._qdrant.scroll(
            COLLECTION_NAME,
            filter_payload={"document_id": document_id},
            limit=limit,
            offset=offset,
        )
        records = []
        for p in points:
            payload = p.get("payload", {})
            # LlamaIndex 的 _node_content 包含完整文本，取前 200 字符作为预览
            content = str(payload.get("_node_content", ""))[:200]
            records.append(QdrantVectorRecord(
                point_id=p["id"],
                chunk_id=str(payload.get("chunk_id", "")),
                filename=str(payload.get("filename", "")),
                content_preview=content,
            ))
        return records, next_offset

    def delete_vectors(self, document_id: int) -> int:
        """删除指定文档的所有向量，返回删除数量"""
        before = self._qdrant.count(COLLECTION_NAME, filter_payload={"document_id": document_id})
        self._qdrant.delete_by_filter(COLLECTION_NAME, filter_payload={"document_id": document_id})
        return before

    def delete_vector(self, point_id: str) -> bool:
        """删除单个向量"""
        try:
            self._qdrant.delete_by_filter(COLLECTION_NAME, filter_payload={"point_id": point_id})
            return True
        except Exception:
            return False

    # ── 语义搜索 ─────────────────────────────────────────

    async def search(
        self, db: AsyncSession, query: str, limit: int = 10,
    ) -> KnowledgeSearchResponse:
        """语义搜索"""
        if not self._rag_pipeline or not self._rag_pipeline.is_ready:
            return KnowledgeSearchResponse(items=[], total=0)

        results = await self._rag_pipeline.search_with_scores(query, limit=limit)

        items = []
        for r in results:
            items.append(KnowledgeSearchResult(
                document_id=r.get("document_id", 0),
                filename=r.get("filename", ""),
                content=r.get("content", ""),
                score=r.get("score", 0),
            ))

        return KnowledgeSearchResponse(items=items, total=len(items))

    # ── 内部方法 ─────────────────────────────────────────

    async def _process_document(self, db: AsyncSession, doc_id: int, file_path: str, filename: str):
        """处理文档：解析 → 分块 → 向量化"""
        if not self._rag_pipeline:
            raise StorageError("RAG 管道未初始化")

        # 更新状态为处理中
        await self.doc_repo.set_status(db, doc_id, 1)

        # 调用 RAG 管道入库
        result = await self._rag_pipeline.ingest_document(file_path, filename, doc_id)

        # 更新分块数和状态
        await self.doc_repo.update(db, doc_id, {
            "chunk_count": result["chunks"],
            "status": 2,  # 完成
        })

        # 清理临时文件
        try:
            os.remove(file_path)
        except OSError:
            pass

    @staticmethod
    def _to_out(item) -> KnowledgeDocumentOut:
        """ORM → Pydantic"""
        return KnowledgeDocumentOut.model_validate(item)

    @staticmethod
    def _chunk_to_out(item) -> KnowledgeChunkOut:
        """ORM → Pydantic"""
        return KnowledgeChunkOut.model_validate(item)


# ── 全局单例 ──────────────────────────────────────────────

knowledge_service = KnowledgeService()
