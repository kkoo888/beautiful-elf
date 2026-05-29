"""SQLAlchemy 基础模型 - 所有业务表的通用字段"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, func
from app.core.database import Base


class BaseModel(Base):
    """所有业务表基类，包含通用字段"""
    __abstract__ = True

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    deleted = Column(Integer, nullable=False, default=0, comment="软删除 (0=正常, 1=已删除)")
    created_at = Column(
        DateTime, nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
