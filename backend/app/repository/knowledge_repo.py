"""知识库 Repository — 封装 KnowledgeDocument / KnowledgeChunk CRUD"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk


class KnowledgeDocumentRepo:
    """知识库文档 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(KnowledgeDocument)

    async def find_by_id(self, db: AsyncSession, id: int) -> Optional[KnowledgeDocument]:
        return await self.mapper.find_by_id(db, id)

    async def find_all(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        status: Optional[int] = None,
    ) -> List[KnowledgeDocument]:
        filters = {}
        if status is not None:
            filters["status"] = status
        return await self.mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count(self, db: AsyncSession, status: Optional[int] = None) -> int:
        filters = {}
        if status is not None:
            filters["status"] = status
        return await self.mapper.count(db, filters=filters)

    async def create(self, db: AsyncSession, data: dict) -> KnowledgeDocument:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, id: int, data: dict) -> Optional[KnowledgeDocument]:
        return await self.mapper.update(db, id, data)

    async def soft_delete(self, db: AsyncSession, id: int) -> bool:
        return await self.mapper.soft_delete(db, id)

    async def set_status(self, db: AsyncSession, id: int, status: int, error_message: str = "") -> bool:
        """更新文档处理状态"""
        data = {"status": status}
        if error_message:
            data["error_message"] = error_message
        result = await self.mapper.update(db, id, data)
        return result is not None

    async def increment_chunk_count(self, db: AsyncSession, id: int, count: int = 1) -> bool:
        """增加分块计数"""
        doc = await self.find_by_id(db, id)
        if not doc:
            return False
        await self.mapper.update(db, id, {"chunk_count": doc.chunk_count + count})
        return True


class KnowledgeChunkRepo:
    """知识库分块 Repository"""

    def __init__(self):
        self.mapper = MySQLMapper(KnowledgeChunk)

    async def find_by_document(
        self, db: AsyncSession, document_id: int, offset: int = 0, limit: int = 100,
    ) -> List[KnowledgeChunk]:
        """获取文档的所有分块"""
        return await self.mapper.find_all(
            db, filters={"document_id": document_id}, offset=offset, limit=limit,
        )

    async def create(self, db: AsyncSession, data: dict) -> KnowledgeChunk:
        return await self.mapper.create(db, data)

    async def bulk_create(self, db: AsyncSession, items: List[dict]) -> None:
        return await self.mapper.bulk_create(db, items)

    async def delete_by_document(self, db: AsyncSession, document_id: int) -> bool:
        """删除文档的所有分块（硬删除，向量由 Qdrant 管理）"""
        from sqlalchemy import delete as sql_delete
        stmt = sql_delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount > 0

    async def count_by_document(self, db: AsyncSession, document_id: int) -> int:
        return await self.mapper.count(db, filters={"document_id": document_id})
