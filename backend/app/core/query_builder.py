"""
查询构建器 - 提供流畅的查询API
减少SQLAlchemy样板代码
"""
from typing import TypeVar, Generic, Type, Optional, List, Any, Dict, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import DeclarativeBase

T = TypeVar('T', bound=DeclarativeBase)


class QueryBuilder(Generic[T]):
    """
    查询构建器，支持链式调用：
    
    users = await (QueryBuilder(User, session)
        .filter(User.age > 18)
        .filter(User.status == "active")
        .order_by(User.created_at, desc=True)
        .paginate(page=1, page_size=20)
        .all())
    """
    
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session
        self._query = select(model)
        self._filters = []
        self._order_by = []
        self._limit = None
        self._offset = None
        self._joins = []
    
    def filter(self, *conditions) -> 'QueryBuilder[T]':
        """添加过滤条件"""
        self._filters.extend(conditions)
        return self
    
    def filter_by(self, **kwargs) -> 'QueryBuilder[T]':
        """按字段过滤"""
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                self._filters.append(getattr(self.model, key) == value)
        return self
    
    def order_by(self, column, desc_order: bool = False) -> 'QueryBuilder[T]':
        """排序"""
        if desc_order:
            self._order_by.append(desc(column))
        else:
            self._order_by.append(asc(column))
        return self
    
    def paginate(self, page: int = 1, page_size: int = 20) -> 'QueryBuilder[T]':
        """分页"""
        self._limit = page_size
        self._offset = (page - 1) * page_size
        return self
    
    def limit(self, limit: int) -> 'QueryBuilder[T]':
        """限制数量"""
        self._limit = limit
        return self
    
    def offset(self, offset: int) -> 'QueryBuilder[T]':
        """偏移量"""
        self._offset = offset
        return self
    
    def join(self, target, *conditions) -> 'QueryBuilder[T]':
        """JOIN查询"""
        self._joins.append((target, conditions))
        return self
    
    def _build_query(self):
        """构建查询"""
        query = select(self.model)
        
        # 应用JOIN
        for target, conditions in self._joins:
            query = query.join(target, *conditions)
        
        # 应用过滤条件
        if self._filters:
            query = query.where(and_(*self._filters))
        
        # 应用排序
        if self._order_by:
            query = query.order_by(*self._order_by)
        
        # 应用分页
        if self._offset:
            query = query.offset(self._offset)
        if self._limit:
            query = query.limit(self._limit)
        
        return query
    
    async def all(self) -> List[T]:
        """获取所有结果"""
        query = self._build_query()
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def first(self) -> Optional[T]:
        """获取第一个结果"""
        query = self._build_query().limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def count(self) -> int:
        """统计数量"""
        query = select(func.count()).select_from(self.model)
        
        if self._filters:
            query = query.where(and_(*self._filters))
        
        result = await self.session.execute(query)
        return result.scalar()
    
    async def exists(self) -> bool:
        """检查是否存在"""
        count = await self.count()
        return count > 0
    
    async def scalar(self) -> Any:
        """获取单个值"""
        query = self._build_query()
        result = await self.session.execute(query)
        return result.scalar()


class BulkOperations:
    """
    批量操作工具类
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def bulk_insert(self, model: Type[T], data_list: List[Dict[str, Any]]) -> int:
        """批量插入"""
        if not data_list:
            return 0
        
        records = [model(**data) for data in data_list]
        self.session.add_all(records)
        await self.session.flush()
        return len(records)
    
    async def bulk_update(self, model: Type[T], filters: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        """批量更新"""
        stmt = update(model).where(
            *[getattr(model, k) == v for k, v in filters.items()]
        ).values(**update_data)
        
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
    
    async def bulk_delete(self, model: Type[T], filters: Dict[str, Any]) -> int:
        """批量删除"""
        stmt = delete(model).where(
            *[getattr(model, k) == v for k, v in filters.items()]
        )
        
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
