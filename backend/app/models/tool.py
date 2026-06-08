"""工具模型（MCP 规范: inputSchema + outputSchema + version）

v3.0 变更:
  - 新增 version 字段（FastMCP v3 组件版本管理）
  - 新增 timeout_seconds 字段（FastMCP v3 工具超时）

来源: https://gofastmcp.com/servers/tools (version, timeout 参数)
"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, Index
from app.models.base import BaseModel


class Tool(BaseModel):
    __tablename__ = "tool"

    name = Column(String(128), nullable=False, unique=True, comment="工具名称")
    display_name = Column(String(256), default="", comment="显示名称")
    description = Column(String(1024), nullable=False, comment="工具描述")
    module = Column(String(128), nullable=False, comment="功能类别")
    json_schema = Column(JSON, nullable=False, comment="参数 JSON Schema (MCP inputSchema)")
    output_schema = Column(JSON, nullable=True, comment="输出 JSON Schema (MCP outputSchema, 可选)")
    risk_level = Column(String(16), nullable=False, default="low", comment="风险等级: low/medium/high")
    is_enabled = Column(Integer, nullable=False, default=1, comment="是否启用: 1=是 0=否")
    version = Column(String(32), nullable=False, default="1.0.0", comment="工具版本号（FastMCP v3 组件版本管理）")
    timeout_seconds = Column(Integer, nullable=False, default=60, comment="工具执行超时（秒），FastMCP v3 timeout")

    __table_args__ = (
        Index("idx_tool_module", "module"),
        Index("idx_tool_is_deleted_enabled", "is_deleted", "is_enabled"),
    )


class ToolStats(BaseModel):
    __tablename__ = "tool_stat"

    tool_id = Column(BigInteger, nullable=False, comment="工具 ID")
    call_count = Column(Integer, nullable=False, default=0, comment="调用次数")
    success_count = Column(Integer, nullable=False, default=0, comment="成功次数")
    fail_count = Column(Integer, nullable=False, default=0, comment="失败次数")
    avg_duration_ms = Column(Integer, nullable=False, default=0, comment="平均耗时")
    last_called_at = Column(DateTime, default=None, comment="最后调用时间")

    __table_args__ = (
        Index("idx_tool_stat_tool_id", "tool_id"),
        Index("idx_tool_stat_call_count", "call_count"),
    )
