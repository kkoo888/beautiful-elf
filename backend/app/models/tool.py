"""工具模型"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, Index
from app.models.base import BaseModel


class Tool(BaseModel):
    __tablename__ = "tools"

    name = Column(String(128), nullable=False, unique=True, comment="工具名称")
    display_name = Column(String(256), default="", comment="显示名称")
    description = Column(String(1024), nullable=False, comment="工具描述")
    module = Column(String(128), nullable=False, comment="所属模块")
    json_schema = Column(JSON, nullable=False, comment="参数 JSON Schema")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")

    __table_args__ = (
        Index("idx_tools_module", "module"),
        Index("idx_tools_enabled", "deleted", "enabled"),
    )


class ToolStats(BaseModel):
    __tablename__ = "tool_stats"

    tool_id = Column(BigInteger, nullable=False, comment="工具 ID")
    call_count = Column(Integer, nullable=False, default=0, comment="调用次数")
    success_count = Column(Integer, nullable=False, default=0, comment="成功次数")
    fail_count = Column(Integer, nullable=False, default=0, comment="失败次数")
    avg_duration_ms = Column(Integer, nullable=False, default=0, comment="平均耗时")
    last_called_at = Column(DateTime, default=None, comment="最后调用时间")

    __table_args__ = (
        Index("idx_tool_stats_tool", "tool_id"),
        Index("idx_tool_stats_calls", "call_count"),
    )
