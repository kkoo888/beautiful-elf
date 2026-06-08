"""MCP Server — 完整 MCP 规范实现（v2.1 全 DB 驱动）

v2.1: 移除静态工具，全部从 DB 加载
v2.0: DB 驱动 + Resources/Prompts + outputSchema

架构:
  MySQL tool 表 → ToolRegistry → FastMCP Server → MCP 协议 → Agent / 外部客户端

规范依据: MCP 2025-06-18 (https://modelcontextprotocol.io/specification/2025-06-18)
"""
from typing import Any
import json

from fastmcp import FastMCP

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── MCP Server 实例 ──────────────────────────────────────

mcp_app = FastMCP(
    "beautiful-elf-tools",
    version="2.1.0",
)


# ── 工具注册（全 DB 驱动）──────────────────────────────────

async def register_tools_from_db(tool_registry) -> int:
    """从 ToolRegistry 加载所有启用的工具到 MCP Server

    MCP 规范:
      - name: 唯一标识符
      - description: 人类可读描述
      - inputSchema: JSON Schema（参数定义）
      - outputSchema: JSON Schema（输出定义，可选）
    """
    from app.core.database import AsyncSessionLocal
    from app.repository.tool_repo import ToolRepository

    repo = ToolRepository()
    async with AsyncSessionLocal() as db:
        tools = await repo.find_all(db, offset=0, limit=1000, enabled=1)

    count = 0
    for tool in tools:
        _register_mcp_tool(tool.name, tool.description, tool.json_schema, tool.output_schema)
        count += 1

    logger.info(f"MCP Server: 从 DB 加载 {count} 个工具")
    return count


def _register_mcp_tool(name: str, description: str, input_schema: dict, output_schema: dict = None):
    """注册单个 MCP 工具（从 DB 元数据 + ToolRegistry 执行函数）"""
    from app.agent.tool_registry import tool_registry

    async def tool_func(**kwargs) -> Any:
        result = await tool_registry.execute(name, kwargs, approved=True)
        return result

    tool_func.__name__ = name
    tool_func.__doc__ = description

    mcp_app.add_tool(
        tool_func,
        name=name,
        description=description,
    )


# ── 工具发现 ─────────────────────────────────────────────

@mcp_app.tool()
async def list_available_tools() -> dict:
    """列出所有可用的工具及其 MCP 元数据（inputSchema + outputSchema）。"""
    from app.agent.tool_registry import tool_registry

    tools = []
    for t in tool_registry.list_tools():
        tool_def = {
            "name": t.name,
            "description": t.description,
            "inputSchema": t.parameters or {"type": "object", "properties": {}},
            "risk_level": t.risk_level.value,
            "module": t.module,
        }
        if t.output_schema:
            tool_def["outputSchema"] = t.output_schema
        tools.append(tool_def)

    return {
        "tools": tools,
        "count": len(tools),
        "protocol": "mcp",
        "version": "2025-06-18",
        "server": "beautiful-elf-tools",
    }


# ── Resources（MCP 规范: 上下文数据）──────────────────────

@mcp_app.resource("config://app")
async def get_app_config() -> str:
    """应用配置信息（MCP Resource）"""
    from app.core.config import get_settings
    settings = get_settings()
    return json.dumps({
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "debug": settings.DEBUG,
    }, ensure_ascii=False)


@mcp_app.resource("config://llm")
async def get_llm_config() -> str:
    """LLM 供应商配置摘要（MCP Resource，不含敏感信息）"""
    from app.core.database import AsyncSessionLocal
    from app.repository.llm_provider_repo import LLMProviderRepository

    repo = LLMProviderRepository()
    async with AsyncSessionLocal() as db:
        providers = await repo.find_all(db, offset=0, limit=100)

    summary = []
    for p in providers:
        summary.append({
            "id": p.id,
            "name": p.name,
            "type": p.provider_type,
            "base_url": p.base_url,
            "is_enabled": getattr(p, 'is_enabled', 1),
        })

    return json.dumps(summary, ensure_ascii=False)


# ── Prompts（MCP 规范: 预定义提示词模板）──────────────────

@mcp_app.prompt()
def chat_assistant() -> str:
    """通用对话助手提示词"""
    return (
        "你是 Beautiful-Elf 智能助手，能够使用工具回答用户问题。\n"
        "请用中文回答，保持友好、专业的语气。"
    )


@mcp_app.prompt()
def code_reviewer(code: str, language: str = "python") -> str:
    """代码审查提示词"""
    return f"""请审查以下 {language} 代码，从以下维度分析：
1. 代码质量 — 命名、结构、可读性
2. 潜在 Bug — 边界情况、异常处理
3. 性能 — 是否有性能问题
4. 安全 — 是否有安全隐患

代码:
```{language}
{code}
```

请用中文输出审查结果。"""


@mcp_app.prompt()
def data_analyst(data_description: str, question: str) -> str:
    """数据分析提示词"""
    return f"""你是一位资深数据分析师。

数据描述：{data_description}

请分析以下问题：{question}

要求：
1. 用数据说话，给出具体数字
2. 提供可视化建议
3. 给出可操作的结论"""


# ── 入口 ─────────────────────────────────────────────────

async def init_mcp_server(tool_registry):
    """初始化 MCP Server（从 DB 加载工具）"""
    try:
        count = await register_tools_from_db(tool_registry)
        logger.info(f"MCP Server 初始化完成: {count} 个工具, Resources + Prompts 就绪")
    except Exception as e:
        logger.error(f"MCP Server 初始化失败: {e}")
        raise


def run_server(host: str = "0.0.0.0", port: int = 8765):
    """启动 MCP Server（SSE 传输）"""
    logger.info(f"MCP Server 启动: {host}:{port}")
    mcp_app.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    import os
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8765"))
    run_server(host, port)
