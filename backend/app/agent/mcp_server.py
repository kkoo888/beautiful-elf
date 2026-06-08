"""MCP Server — 完整 MCP 规范实现（v3.0 FastMCP v3 + MCP 2025-06-18）

v3.0: 升级 FastMCP v3，全面支持 MCP 2025-06-18 规范
  - Streamable HTTP 传输（替代 SSE）
  - Elicitation（高风险工具二次确认，通过 Context 注入）
  - Resource Links（工具结果关联 Resource，content 内嵌）
  - 组件版本管理（FastMCP v3 VersionFilter + LocalProvider）
  - Tool 超时控制（FastMCP v3 timeout 参数）
  - 结构化签名（动态生成匹配 inputSchema 的函数签名）
  - title 字段（MCP 2025-06-18 显示友好名称）
  - isError 响应字段（MCP 规范要求标识执行错误）
  - tools/list cursor 分页（MCP 规范要求）
  - listChanged 通知（工具热加载时自动触发）
  - Sampling 支持（服务端请求 Client 进行 LLM 推理，多角色专家团场景）
  - Progress Tracking（长任务进度追踪，专家团场景必备）

架构:
  MySQL tool 表 → ToolRegistry → FastMCP Server → MCP 协议 → Agent / 外部客户端

规范依据:
  - MCP 2025-06-18: https://modelcontextprotocol.io/specification/2025-06-18
  - FastMCP v3: https://gofastmcp.com (PyPI: fastmcp>=3.4.0)
  - FastMCP Tools: https://gofastmcp.com/servers/tools
  - FastMCP Elicitation: https://gofastmcp.com/servers/elicitation
  - FastMCP Versioning: https://gofastmcp.com/servers/versioning
  - FastMCP 升级指南: https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2

关键修复记录:
  - 修复: **kwargs 不被 FastMCP 支持，改用动态生成的类型化签名
  - 修复: Context 注入通过函数签名类型注解实现，而非 kwargs
  - 修复: Resource Links 改为 MCP 规范的 content 内嵌格式
  - 修复: Elicitation 通过 Context 参数正确注入
  - 移除: confirm_dangerous_action 演示工具（非生产代码）
"""
from typing import Any, Optional
import inspect
import json
import time
import functools

from fastmcp import FastMCP, Context

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── MCP Server 实例 ──────────────────────────────────────

mcp_app = FastMCP(
    "beautiful-elf-tools",
    version="3.0.0",
)


# ── 动态函数签名生成 ─────────────────────────────────────

def _build_tool_wrapper(
    name: str,
    description: str,
    input_schema: dict,
    is_high_risk: bool,
) -> callable:
    """为 DB 驱动的工具创建类型化包装函数

    关键: FastMCP 要求工具函数有完整的类型化签名（不支持 **kwargs）。
    此函数根据 DB 中的 inputSchema 动态生成匹配的函数签名，
    让 FastMCP 能正确生成 MCP inputSchema 并注入 Context。

    来源:
      - https://gofastmcp.com/servers/tools ("Functions with **kwargs are not supported")
      - https://gofastmcp.com/servers/elicitation (ctx.elicit() 通过 Context 注入)
    """
    from app.agent.tool_registry import tool_registry
    from fastmcp.server.elicitation import AcceptedElicitation, DeclinedElicitation, CancelledElicitation

    # 从 input_schema 构建函数参数
    params = []
    properties = (input_schema or {}).get("properties", {})
    required_fields = set((input_schema or {}).get("required", []))

    for param_name, param_info in properties.items():
        param_type = _json_type_to_python(param_info.get("type", "string"))
        param_desc = param_info.get("description", "")
        is_required = param_name in required_fields

        if is_required:
            default = inspect.Parameter.empty
        else:
            default = param_info.get("default", None)

        annotation = param_type
        params.append(
            inspect.Parameter(
                param_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=annotation,
            )
        )

    # 添加 Context 参数（FastMCP 会自动注入）
    params.append(
        inspect.Parameter(
            "ctx",
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=None,
            annotation=Optional[Context],
        )
    )

    # 构建函数签名
    sig = inspect.Signature(params, return_annotation=dict)

    # 创建包装函数（用 exec 绑定闭包变量）
    async def tool_wrapper(**kwargs) -> dict:
        start = time.time()
        ctx = kwargs.pop("ctx", None)

        # 高风险工具: Elicitation 二次确认
        # 来源: https://gofastmcp.com/servers/elicitation
        if is_high_risk and ctx:
            try:
                result = await ctx.elicit(
                    message=f"⚠️ 即将执行高风险操作「{name}」，确认继续？",
                    response_type=str,
                )
                match result:
                    case AcceptedElicitation():
                        pass
                    case DeclinedElicitation():
                        return {"cancelled": True, "message": "用户拒绝执行该操作"}
                    case CancelledElicitation():
                        return {"cancelled": True, "message": "用户取消了操作"}
            except Exception as e:
                logger.warning(f"Elicitation 失败（Client 可能不支持）: {e}，跳过确认继续执行")

        # 执行工具（附带进度通知）
        if ctx:
            try:
                await ctx.report_progress(progress=0, total=100, message=f"开始执行 {name}")
            except Exception:
                pass

        exec_result = await tool_registry.execute(name, kwargs, approved=True)
        duration_ms = int((time.time() - start) * 1000)

        if ctx:
            try:
                await ctx.report_progress(progress=100, total=100, message=f"{name} 执行完成")
            except Exception:
                pass

        # 包装为 MCP 规范的 Tool Result 格式
        # Resource Links 内嵌在 content 中（非顶层字段）
        # 来源: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
        content = []
        resource_links = _build_resource_links(name, exec_result)

        if isinstance(exec_result, dict):
            exec_result["_duration_ms"] = duration_ms
            content.append({"type": "text", "text": json.dumps(exec_result, ensure_ascii=False, default=str)})
        else:
            content.append({"type": "text", "text": str(exec_result)})

        # Resource Links 作为 content 的一部分
        for link in resource_links:
            content.append({
                "type": "resource_link",
                "uri": link["uri"],
                "name": link["name"],
                "description": link.get("description", ""),
            })

        # isError: MCP 2025-06-18 规范要求标识工具执行是否出错
        is_error = isinstance(exec_result, dict) and (
            exec_result.get("error") or exec_result.get("cancelled")
        )
        return {"content": content, "isError": bool(is_error)}

    # 设置函数元数据（FastMCP 从中读取 name/description/signature）
    tool_wrapper.__name__ = name
    tool_wrapper.__qualname__ = name
    tool_wrapper.__doc__ = description
    tool_wrapper.__signature__ = sig

    return tool_wrapper


def _json_type_to_python(json_type: str) -> type:
    """JSON Schema 类型 → Python 类型"""
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return mapping.get(json_type, Any)


# ── 工具注册（全 DB 驱动）──────────────────────────────────

async def register_tools_from_db(tool_registry) -> int:
    """从 ToolRegistry 加载所有启用的工具到 MCP Server

    MCP 规范:
      - name: 唯一标识符
      - description: 人类可读描述
      - inputSchema: 由 FastMCP 从函数签名自动生成
      - outputSchema: JSON Schema（可选）
      - version: 工具版本号（FastMCP v3 组件版本管理）

    FastMCP v3 变更:
      - add_tool() 不支持 **kwargs，必须有类型化签名
      - add_tool() 支持 version/timeout/output_schema 参数
      - Context 通过函数签名的类型注解自动注入

    来源: https://gofastmcp.com/servers/tools
    """
    from app.core.database import AsyncSessionLocal
    from app.repository.tool_repo import ToolRepository

    repo = ToolRepository()
    async with AsyncSessionLocal() as db:
        tools = await repo.find_all(db, offset=0, limit=1000, enabled=1)

    count = 0
    for tool in tools:
        tool_version = getattr(tool, 'version', None) or "1.0.0"
        timeout = getattr(tool, 'timeout_seconds', None) or 60
        risk_level = getattr(tool, 'risk_level', 'low')
        output_schema = getattr(tool, 'output_schema', None)

        _register_mcp_tool(
            name=tool.name,
            description=tool.description,
            input_schema=tool.json_schema,
            output_schema=output_schema,
            risk_level=risk_level,
            version=tool_version,
            timeout=timeout,
            title=getattr(tool, 'display_name', None) or None,
        )
        count += 1

    logger.info(f"MCP Server: 从 DB 加载 {count} 个工具")
    return count


def _register_mcp_tool(
    name: str,
    description: str,
    input_schema: dict,
    output_schema: dict = None,
    risk_level: str = "low",
    version: str = "1.0.0",
    timeout: int = 60,
    title: str = None,
):
    """注册单个 MCP 工具（DB 元数据 + 动态签名 + v3 增强）"""
    is_high_risk = risk_level in ("high",)

    # 动态生成类型化包装函数（解决 **kwargs 问题）
    tool_func = _build_tool_wrapper(
        name=name,
        description=description,
        input_schema=input_schema,
        is_high_risk=is_high_risk,
    )

    # FastMCP v3 add_tool: 支持 version + timeout + output_schema
    # 来源: https://gofastmcp.com/servers/tools (Decorator Arguments)
    add_kwargs = {
        "name": name,
        "description": description,
        "version": version,
        "timeout": timeout,
    }
    if title:
        add_kwargs["title"] = title
    if output_schema:
        add_kwargs["output_schema"] = output_schema

    mcp_app.add_tool(tool_func, **add_kwargs)


# ── Resource Links 构建 ──────────────────────────────────

def _build_resource_links(tool_name: str, result: Any) -> list:
    """构建 Resource Links（MCP 2025-06-18）

    工具执行结果关联到相关 Resource，让 Client 可以按需 fetch 更多上下文。
    返回格式: [{"uri": "...", "name": "...", "description": "..."}]

    来源: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
    """
    links = []
    tool_lower = tool_name.lower()

    if any(kw in tool_lower for kw in ("llm", "model", "ai", "chat", "completion")):
        links.append({
            "uri": "config://llm",
            "name": "LLM 供应商配置",
            "description": "当前可用的 LLM 供应商和模型配置",
        })

    if any(kw in tool_lower for kw in ("config", "setting", "system")):
        links.append({
            "uri": "config://app",
            "name": "应用配置",
            "description": "当前应用的全局配置信息",
        })

    if isinstance(result, dict) and result.get("error"):
        links.append({
            "uri": "config://tools",
            "name": "工具列表",
            "description": "查看所有可用工具及其状态",
        })

    return links


# ── Progress Tracking（长任务进度追踪）──────────────────
# MCP 2025-06-18 规范: 工具执行过程中可向 Client 推送进度
# 场景: 专家团任务、批量数据处理、代码分析等耗时操作
# 使用: 工具函数签名声明 ctx: Context，然后调用 ctx.report_progress()
#
# 来源: https://modelcontextprotocol.io/specification/2025-06-18/server/utilities/progress


class ProgressTracker:
    """进度追踪器 — 封装 MCP Progress 通知

    用法:
        tracker = ProgressTracker(ctx, total=100)
        for i in range(100):
            do_work(i)
            await tracker.update(1, f"处理第 {i+1} 条")
        await tracker.done("全部完成")
    """

    def __init__(self, ctx: Context, total: int = 100):
        self.ctx = ctx
        self.total = total
        self.current = 0

    async def update(self, increment: int = 1, message: str = ""):
        """更新进度"""
        self.current += increment
        if self.ctx:
            try:
                await self.ctx.report_progress(
                    progress=self.current,
                    total=self.total,
                    message=message,
                )
            except Exception:
                pass  # Client 不支持进度通知时静默忽略

    async def done(self, message: str = "完成"):
        """标记任务完成"""
        self.current = self.total
        if self.ctx:
            try:
                await self.ctx.report_progress(
                    progress=self.total,
                    total=self.total,
                    message=message,
                )
            except Exception:
                pass


# ── Sampling（服务端请求 Client 进行 LLM 推理）──────────
# MCP 2025-06-18 规范: Server 可请求 Client 执行 LLM 采样
# 场景: 工具内部需要 LLM 帮忙思考（多角色专家团、代码审查、数据分析等）
# 关键: 调用 LLM 的决定权在 Client（用户侧），Server 不能直接调
#
# 使用方式: 在工具函数签名中声明 ctx: Context，然后调用:
#   result = await sample_via_client(ctx, prompt, max_tokens=4096)
#
# 来源: https://modelcontextprotocol.io/specification/2025-06-18/client/sampling

async def sample_via_client(
    ctx: Context,
    prompt: str,
    max_tokens: int = 4096,
    model_preferences: dict = None,
    system_prompt: str = None,
    include_context: str = "thisServer",
) -> dict:
    """通过 Client 请求 LLM 采样（Sampling）

    Args:
        ctx: FastMCP Context（工具函数签名中声明即可自动注入）
        prompt: 发给 LLM 的提示词
        max_tokens: 最大生成 token 数
        model_preferences: 模型偏好（hints: speedPriority / intelligencePriority）
        system_prompt: 系统提示词（可选）
        include_context: 上下文包含策略（"none"/"thisServer"/"allServers"）

    Returns:
        {"role": "assistant", "content": {"type": "text", "text": "..."}, "model": "..."}
        或 {"error": "..."} 如果 Client 不支持 Sampling
    """
    try:
        # FastMCP v3: ctx.sample() 封装了 MCP Sampling 协议
        result = await ctx.sample(
            messages=prompt,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            include_context=include_context,
        )
        # FastMCP v3: ctx.sample() 返回 SamplingResult，用 .text 取文本
        # 来源: https://gofastmcp.com/servers/sampling
        text = result.text if hasattr(result, 'text') else str(result)
        return {"role": "assistant", "content": {"type": "text", "text": text or ""}}
    except Exception as e:
        logger.warning(f"Sampling 请求失败（Client 可能不支持）: {e}")
        return {"error": f"Sampling 不可用: {e}", "code": "SAMPLING_NOT_SUPPORTED"}


# ── 工具发现 ─────────────────────────────────────────────

@mcp_app.tool()
async def list_available_tools(cursor: str = "") -> dict:
    """列出所有可用的工具及其 MCP 元数据（inputSchema + outputSchema）。

    支持 cursor 分页（MCP 2025-06-18 规范）。
    cursor 格式: 工具在列表中的偏移量（字符串化的数字）。
    """
    from app.agent.tool_registry import tool_registry

    all_tools = tool_registry.list_tools()
    page_size = 50

    # 解析 cursor（偏移量）
    offset = 0
    if cursor:
        try:
            offset = int(cursor)
        except (ValueError, TypeError):
            offset = 0

    # 分页切片
    page_tools = all_tools[offset:offset + page_size]
    next_offset = offset + page_size

    tools = []
    for t in page_tools:
        tool_def = {
            "name": t.name,
            "title": getattr(t, 'display_name', None) or t.name,
            "description": t.description,
            "inputSchema": t.parameters or {"type": "object", "properties": {}},
            "risk_level": t.risk_level.value,
            "module": t.module,
        }
        if t.output_schema:
            tool_def["outputSchema"] = t.output_schema
        tools.append(tool_def)

    result = {
        "tools": tools,
        "count": len(tools),
        "protocol": "mcp",
        "version": "2025-06-18",
        "server": "beautiful-elf-tools",
    }

    # 有下一页时返回 nextCursor
    if next_offset < len(all_tools):
        result["nextCursor"] = str(next_offset)

    return result


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


@mcp_app.resource("config://tools")
async def get_tools_config() -> str:
    """工具列表摘要（MCP Resource，供 Resource Links 关联）"""
    from app.agent.tool_registry import tool_registry

    tools = []
    for t in tool_registry.list_tools():
        tools.append({
            "name": t.name,
            "description": t.description,
            "risk_level": t.risk_level.value,
            "module": t.module,
            "enabled": True,
        })

    return json.dumps({
        "tools": tools,
        "count": len(tools),
    }, ensure_ascii=False)


# ── Prompts（MCP 规范: 预定义提示词模板）──────────────────
# FastMCP v3: Prompt 返回 str 即可（v2 的 dict 返回不再支持）
# 来源: https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2

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


# ── 运行时热加载（listChanged 通知）──────────────────────

async def reload_tools(tool_registry) -> int:
    """运行时重新加载工具列表（DB 变更后调用）

    MCP 规范: 工具列表变更时发送 notifications/tools/list_changed
    FastMCP v3: add_tool() 会自动触发 listChanged 通知

    来源: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
    """
    from app.core.database import AsyncSessionLocal
    from app.repository.tool_repo import ToolRepository

    repo = ToolRepository()
    async with AsyncSessionLocal() as db:
        tools = await repo.find_all(db, offset=0, limit=1000, enabled=1)

    # FastMCP v3: 移除旧工具再重新注册，会自动发送 listChanged 通知
    try:
        existing_names = {t.name for t in mcp_app._tool_manager.list_tools()}
    except AttributeError:
        # FastMCP 内部 API 变更时降级：不清理旧工具，只做增量注册
        existing_names = set()
    new_names = {tool.name for tool in tools}

    # 移除已禁用/删除的工具
    for name in existing_names - new_names:
        try:
            mcp_app.remove_tool(name)
            logger.info(f"[reload] 移除工具: {name}")
        except Exception:
            pass

    # 注册/更新工具
    count = 0
    for tool in tools:
        tool_version = getattr(tool, 'version', None) or "1.0.0"
        timeout = getattr(tool, 'timeout_seconds', None) or 60
        risk_level = getattr(tool, 'risk_level', 'low')
        output_schema = getattr(tool, 'output_schema', None)

        _register_mcp_tool(
            name=tool.name,
            description=tool.description,
            input_schema=tool.json_schema,
            output_schema=output_schema,
            risk_level=risk_level,
            version=tool_version,
            timeout=timeout,
            title=getattr(tool, 'display_name', None) or None,
        )
        count += 1

    logger.info(f"[reload] 工具热加载完成: {count} 个工具")
    return count


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
    """启动 MCP Server（Streamable HTTP 传输）

    v3.0 变更:
      - transport: "sse" → "http"（Streamable HTTP，MCP 2025-06-18 规范）
      - URL path 默认 /mcp
      - 支持普通 JSON 响应 + SSE 流式响应

    来源: https://gofastmcp.com/getting-started/quickstart
    """
    logger.info(f"MCP Server 启动: {host}:{port} (Streamable HTTP)")
    mcp_app.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    from app.core.config import get_settings
    _settings = get_settings()
    run_server(_settings.MCP_SERVER_HOST, _settings.MCP_SERVER_PORT)
