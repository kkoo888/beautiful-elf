"""SQLAlchemy 基础模型 - 所有业务表的通用字段（SQLAlchemy 2.0 新风格）"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BaseModel(Base):
    """所有业务表基类，包含通用字段"""
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="是否删除: 1=是 0=否")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
