"""MCP Server — FastMCP 包装内置工具

将 ToolRegistry 中的内置工具通过 MCP 协议暴露，供 Agent 和外部客户端调用。

架构:
  ToolRegistry (内置工具) → FastMCP Server → MCP 协议 → Agent / 外部客户端

启动方式:
  - 独立进程: python -m app.agent.mcp_server
  - 嵌入启动: from app.agent.mcp_server import mcp_app; mcp_app.run()
"""
import asyncio
import json
import logging
from typing import Any

from fastmcp import FastMCP

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── MCP Server 实例 ──────────────────────────────────────

mcp_app = FastMCP(
    name="beautiful-elf-tools",
    version="1.0.0",
    description="Beautiful Elf Agent 内置工具 MCP Server",
)


# ── 工具注册 ─────────────────────────────────────────────

@mcp_app.tool()
async def web_search(query: str, max_results: int = 5) -> dict:
    """搜索互联网获取实时信息。

    Args:
        query: 搜索关键词
        max_results: 最大结果数，默认 5
    """
    from app.agent.tool_registry import web_search as _web_search
    return await _web_search(query=query, max_results=max_results)


@mcp_app.tool()
async def execute_code(language: str, code: str) -> dict:
    """在沙箱中执行代码（Docker 隔离，10 秒超时）。

    Args:
        language: 编程语言，支持 python 和 javascript
        code: 要执行的代码
    """
    from app.agent.tool_registry import execute_code as _execute_code
    return await _execute_code(language=language, code=code)


@mcp_app.tool()
async def read_file(path: str) -> dict:
    """读取工作空间中的文件内容。

    Args:
        path: 文件路径（相对于工作空间根目录）
    """
    from app.agent.tool_registry import read_file as _read_file
    return await _read_file(path=path)


@mcp_app.tool()
async def query_database(sql: str) -> dict:
    """查询数据库（只允许 SELECT，自动添加 LIMIT 100）。

    Args:
        sql: SQL 查询语句（仅 SELECT）
    """
    from app.agent.tool_registry import query_database as _query_database
    return await _query_database(sql=sql)


# ── 工具发现 ─────────────────────────────────────────────

@mcp_app.tool()
async def list_available_tools() -> dict:
    """列出所有可用的内置工具及其元数据。"""
    from app.agent.tool_registry import tool_registry
    summaries = tool_registry.list_tool_summaries()
    return {
        "tools": summaries,
        "count": len(summaries),
        "protocol": "mcp",
        "server": "beautiful-elf-tools",
    }


# ── 入口 ─────────────────────────────────────────────────

def run_server(host: str = "0.0.0.0", port: int = 8765):
    """启动 MCP Server（SSE 传输）"""
    logger.info(f"MCP Server 启动: {host}:{port}")
    mcp_app.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    import os
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8765"))
    run_server(host, port)
