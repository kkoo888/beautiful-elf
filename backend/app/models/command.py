"""命令模型"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Index
from app.models.base import BaseModel


class Command(BaseModel):
    __tablename__ = "command"

    name = Column(String(128), nullable=False, unique=True, comment="命令名称")
    display_name = Column(String(256), default="", comment="显示名称")
    description = Column(String(512), default="", comment="命令描述")
    shortcut_key = Column(String(32), default="", comment="快捷键")
    module = Column(String(64), nullable=False, comment="所属模块")
    command_type = Column(Integer, nullable=False, default=0, comment="类型")
    is_enabled = Column(Integer, nullable=False, default=1, comment="是否启用: 1=是 0=否")

    __table_args__ = (
        Index("idx_command_module", "module"),
        Index("idx_command_is_deleted_enabled", "is_deleted", "is_enabled"),
    )


class CommandUsage(BaseModel):
    __tablename__ = "command_usage"

    command_id = Column(BigInteger, nullable=False, comment="命令 ID")
    use_count = Column(Integer, nullable=False, default=0, comment="使用次数")
    last_used_at = Column(DateTime, default=None, comment="最后使用时间")

    __table_args__ = (
        Index("idx_command_usage_command_id", "command_id"),
        Index("idx_command_usage_use_count", "use_count"),
    )
