"""工具模型（MCP 规范: inputSchema + outputSchema + annotations）

v3.1 变更:
  - 移除 version 独立字段（MCP 规范无此字段，版本移入 annotations.version）
  - 新增 strict_mode 字段（OpenAI strict 模式，强制 JSON Schema 合规）

v3.0 变更:
  - 新增 timeout_seconds 字段（FastMCP v3 工具超时）
  - 新增 annotations 字段（MCP 2025-06-18 Tool Annotations）

来源:
  - https://modelcontextprotocol.io/specification/2025-06-18/server/tools (annotations)
  - https://platform.openai.com/docs/guides/function-calling (strict mode)
"""
from datetime import datetime

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, Index
from app.models.base import BaseModel


class Tool(BaseModel):
    __tablename__ = "tool"

    name = Column(String(128), nullable=False, unique=True, comment="工具名称")
    display_name = Column(String(256), default="", comment="显示名称")
    description = Column(String(1024), nullable=False, comment="工具描述")
    module = Column(String(128), nullable=False, comment="功能类别")
    json_schema = Column(JSON, nullable=False, comment="参数 JSON Schema (MCP inputSchema)")
    output_schema = Column(JSON, nullable=False, default=dict, comment="输出 JSON Schema (MCP outputSchema)")
    risk_level = Column(String(16), nullable=False, default="low", comment="风险等级: low/medium/high")
    is_enabled = Column(Integer, nullable=False, default=1, comment="是否启用: 1=是 0=否")
    timeout_seconds = Column(Integer, nullable=False, default=60, comment="工具执行超时（秒），FastMCP v3 timeout")
    strict_mode = Column(Integer, nullable=False, default=0, comment="OpenAI strict 模式: 1=启用 0=禁用")
    annotations = Column(JSON, nullable=False, default=dict, comment="MCP Tool Annotations (readOnlyHint/destructiveHint/idempotentHint/openWorldHint)")

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
    last_called_at = Column(DateTime, nullable=False, default=datetime(2000, 1, 1), server_default='2000-01-01 00:00:00', comment="最后调用时间")

    __table_args__ = (
        Index("idx_tool_stat_tool_id", "tool_id"),
        Index("idx_tool_stat_call_count", "call_count"),
    )
