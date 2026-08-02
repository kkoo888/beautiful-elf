"""
基础服务类 - 提供通用CRUD操作和缓存机制
减少重复代码，提高可维护性
"""
from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')  # ORM模型类型
CreateSchema = TypeVar('CreateSchema', bound=BaseModel)
UpdateSchema = TypeVar('UpdateSchema', bound=BaseModel)


class BaseService(Generic[T, CreateSchema, UpdateSchema]):
    """
    基础服务类，提供：
    1. 标准CRUD操作
    2. 批量操作支持
    3. 查询构建器模式
    4. 缓存集成点
    """
    
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session
        self._cache: Dict[str, Any] = {}
    
    async def get_by_id(self, id: Any) -> Optional[T]:
        """根据ID获取单条记录"""
        cache_key = f"{self.model.__name__}:{id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        record = result.scalar_one_or_none()
        
        if record:
            self._cache[cache_key] = record
        return record
    
    async def get_list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        """获取列表，支持过滤、排序、分页"""
        query = select(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        if order_by and hasattr(self.model, order_by):
            query = query.order_by(getattr(self.model, order_by))
        
        query = query.offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, schema: CreateSchema) -> T:
        """创建记录"""
        data = schema.model_dump()
        record = self.model(**data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        self._invalidate_cache()
        return record
    
    async def update(self, id: Any, schema: UpdateSchema) -> Optional[T]:
        """更新记录"""
        record = await self.get_by_id(id)
        if not record:
            return None
        
        data = schema.model_dump(exclude_unset=True)
        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        
        await self.session.flush()
        await self.session.refresh(record)
        self._invalidate_cache()
        return record
    
    async def delete(self, id: Any) -> bool:
        """删除记录"""
        record = await self.get_by_id(id)
        if not record:
            return False
        
        await self.session.delete(record)
        await self.session.flush()
        self._invalidate_cache()
        return True
    
    async def batch_create(self, schemas: List[CreateSchema]) -> List[T]:
        """批量创建"""
        records = []
        for schema in schemas:
            data = schema.model_dump()
            record = self.model(**data)
            self.session.add(record)
            records.append(record)
        
        await self.session.flush()
        for record in records:
            await self.session.refresh(record)
        
        self._invalidate_cache()
        return records
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计数量"""
        query = select(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        result = await self.session.execute(query)
        return len(result.scalars().all())
    
    def _invalidate_cache(self):
        """清除缓存"""
        self._cache.clear()
    
    def clear_cache(self):
        """外部清除缓存接口"""
        self._invalidate_cache()
