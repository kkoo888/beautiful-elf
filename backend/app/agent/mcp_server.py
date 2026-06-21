"""MCP Server — 完整 MCP 规范实现（v3.0 FastMCP v3 + MCP 2025-06-18）

v3.1 重构:
  - ToolResultBuilder: 结果构建独立（content + structuredContent + isError + resourceLinks）
  - ToolAnnotations: MCP 2025-06-18 工具注解（DB 存精确值，risk_level 兜底）
  - 管道拆分: _handle_elicitation / _execute_tool 从 wrapper 提取
  - structuredContent: 有 outputSchema 时必须返回（MCP 规范 MUST）

规范依据:
  - MCP 2025-06-18: https://modelcontextprotocol.io/specification/2025-06-18
  - FastMCP v3: https://gofastmcp.com (PyPI: fastmcp>=3.4.0)
  - FastMCP Tools: https://gofastmcp.com/servers/tools
  - FastMCP Elicitation: https://gofastmcp.com/servers/elicitation
  - FastMCP Versioning: https://gofastmcp.com/servers/versioning

架构:
  MySQL tool 表 → ToolRegistry → FastMCP Server → MCP 协议 → Agent / 外部客户端
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import copy
import inspect
import json
import time

from fastmcp import FastMCP, Context
from fastmcp.tools import FunctionTool as MCPFunctionTool
from mcp.types import ToolAnnotations as MCPToolAnnotations

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── MCP Server 实例 ──────────────────────────────────────

mcp_app = FastMCP(
    "beautiful-elf-tools",
    version="3.1.0",
)


# ══════════════════════════════════════════════════════════
#  ToolAnnotations — MCP 2025-06-18 工具注解
# ══════════════════════════════════════════════════════════
# 规范: https://modelcontextprotocol.io/specification/2025-06-18/server/tools#annotations
# FastMCP: add_tool(annotations=ToolAnnotations(...))
#
# DB 存精确值（tool.annotations JSON 列）。
# from_risk_level() 仅在 DB 值为空时做兜底默认。


@dataclass
class ToolAnnotations:
    """MCP 2025-06-18 Tool Annotations

    Client 根据这些注解智能决策（是否弹确认、是否缓存结果等），
    而不是每次都走 Elicitation。

    字段说明:
      - title: 显示友好名称（与 display_name 对应）
      - readOnlyHint: 工具不修改环境（只读查询）
      - destructiveHint: 工具可能执行破坏性操作（删数据、发邮件）
      - idempotentHint: 重复调用相同参数无额外效果
      - openWorldHint: 工具与外部实体交互（网络请求、文件系统）
    """
    title: str = ""
    readOnlyHint: bool = False
    destructiveHint: bool = False
    idempotentHint: bool = True
    openWorldHint: bool = False

    def to_dict(self) -> dict:
        """转为 FastMCP 接受的 dict 格式"""
        return {
            "title": self.title,
            "readOnlyHint": self.readOnlyHint,
            "destructiveHint": self.destructiveHint,
            "idempotentHint": self.idempotentHint,
            "openWorldHint": self.openWorldHint,
        }

    @classmethod
    def from_db(cls, db_annotations: dict | None, risk_level: str = "low", display_name: str = "") -> ToolAnnotations:
        """从 DB 加载，DB 为空时从 risk_level 推导兜底

        优先级: DB 精确值 > risk_level 推导默认值
        """
        fallback = cls.from_risk_level(risk_level, display_name)
        if not db_annotations:
            return fallback
        return cls(
            title=db_annotations.get("title", fallback.title),
            readOnlyHint=db_annotations.get("readOnlyHint", fallback.readOnlyHint),
            destructiveHint=db_annotations.get("destructiveHint", fallback.destructiveHint),
            idempotentHint=db_annotations.get("idempotentHint", fallback.idempotentHint),
            openWorldHint=db_annotations.get("openWorldHint", fallback.openWorldHint),
        )

    @classmethod
    def from_risk_level(cls, risk_level: str, display_name: str = "") -> ToolAnnotations:
        """从 risk_level 推导默认注解（兜底用）"""
        mapping = {
            "low": cls(title=display_name, readOnlyHint=True, idempotentHint=True, openWorldHint=False),
            "medium": cls(title=display_name, readOnlyHint=False, destructiveHint=False, openWorldHint=True),
            "high": cls(title=display_name, readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True),
        }
        return mapping.get(risk_level, cls(title=display_name))


# ══════════════════════════════════════════════════════════
#  ToolResultBuilder — MCP Tool Result 构建器
# ══════════════════════════════════════════════════════════
# 规范: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
#
# 职责: 一次构建完整的 MCP Tool Result:
#   - content: 非结构化内容（text + resource_link）— 向后兼容
#   - structuredContent: 结构化内容 — 有 outputSchema 时必须返回
#   - isError: 执行是否出错
#
# 关键规则:
#   1. 有 outputSchema 时 MUST 返回 structuredContent
#   2. 同时 SHOULD 在 content 中返回序列化 JSON（向后兼容）
#   3. 不污染原始 exec_result（内部 copy）


class ToolResultBuilder:
    """MCP Tool Result 构建器

    用法:
        result = ToolResultBuilder(
            tool_name="get_weather",
            exec_result={"temp": 22},
            duration_ms=150,
            output_schema={"type": "object", "properties": {...}},
        ).build()
        # → {"content": [...], "structuredContent": {...}, "isError": false}
    """

    def __init__(
        self,
        tool_name: str,
        exec_result: Any,
        duration_ms: int,
        output_schema: dict | None = None,
    ):
        self.tool_name = tool_name
        self.exec_result = exec_result
        self.duration_ms = duration_ms
        self.output_schema = output_schema

    def build(self) -> dict:
        """构建完整的 MCP Tool Result"""
        is_error = self._detect_error()

        result: dict[str, Any] = {
            "content": self._build_content(),
            "isError": is_error,
        }

        # structuredContent: 有 outputSchema 且结果是 dict 时返回
        # 规范: "Servers MUST provide structured results that conform to this schema"
        if self.output_schema and isinstance(self.exec_result, dict):
            result["structuredContent"] = self.exec_result

        return result

    def _build_content(self) -> list[dict]:
        """构建 content 数组（text + resource_links）"""
        content: list[dict] = []

        # text content — copy 一份，不污染原始数据
        if isinstance(self.exec_result, dict):
            data = copy.copy(self.exec_result)
            data["_duration_ms"] = self.duration_ms
            content.append({
                "type": "text",
                "text": json.dumps(data, ensure_ascii=False, default=str),
            })
        else:
            content.append({"type": "text", "text": str(self.exec_result)})

        # resource links — 内嵌在 content 中
        for link in self._build_resource_links():
            content.append({
                "type": "resource_link",
                "uri": link["uri"],
                "name": link["name"],
                "description": link.get("description", ""),
            })

        return content

    def _detect_error(self) -> bool:
        """检测执行是否出错"""
        return isinstance(self.exec_result, dict) and bool(
            self.exec_result.get("error") or self.exec_result.get("cancelled")
        )

    def _build_resource_links(self) -> list[dict]:
        """构建 Resource Links（MCP 2025-06-18）

        工具执行结果关联到相关 Resource，让 Client 按需 fetch 更多上下文。
        规范: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
        """
        links: list[dict] = []
        tool_lower = self.tool_name.lower()

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

        if isinstance(self.exec_result, dict) and self.exec_result.get("error"):
            links.append({
                "uri": "config://tools",
                "name": "工具列表",
                "description": "查看所有可用工具及其状态",
            })

        return links


# ══════════════════════════════════════════════════════════
#  管道组件 — 从 _build_tool_wrapper 提取
# ══════════════════════════════════════════════════════════


async def _handle_elicitation(ctx: Context, tool_name: str) -> dict | None:
    """Elicitation 二次确认（高风险工具）

    规范: MCP 2025-06-18 — 人类在回路（human-in-the-loop）
    FastMCP: https://gofastmcp.com/servers/elicitation

    Returns:
        None → 用户同意，继续执行
        dict → 用户拒绝/取消，直接返回此 dict 作为工具结果
    """
    from fastmcp.server.elicitation import AcceptedElicitation, DeclinedElicitation, CancelledElicitation

    try:
        result = await ctx.elicit(
            message=f"⚠️ 即将执行高风险操作「{tool_name}」，确认继续？",
            response_type=str,
        )
        match result:
            case AcceptedElicitation():
                return None
            case DeclinedElicitation():
                return {"cancelled": True, "message": "用户拒绝执行该操作"}
            case CancelledElicitation():
                return {"cancelled": True, "message": "用户取消了操作"}
    except Exception as e:
        logger.warning(f"Elicitation 失败（Client 可能不支持）: {e}，跳过确认继续执行")
        return None

    return None


async def _execute_tool(
    tool_registry: Any,
    tool_name: str,
    kwargs: dict,
    ctx: Context | None,
) -> tuple[Any, int]:
    """执行工具 + 进度通知

    Returns:
        (exec_result, duration_ms)
    """
    # 进度: 开始
    if ctx:
        try:
            await ctx.report_progress(progress=0, total=100, message=f"开始执行 {tool_name}")
        except Exception:
            pass

    start = time.time()
    exec_result = await tool_registry.execute(tool_name, kwargs, approved=True)
    duration_ms = int((time.time() - start) * 1000)

    # 进度: 完成
    if ctx:
        try:
            await ctx.report_progress(progress=100, total=100, message=f"{tool_name} 执行完成")
        except Exception:
            pass

    return exec_result, duration_ms


def _build_params(input_schema: dict) -> list[inspect.Parameter]:
    """从 inputSchema 构建 inspect.Parameter 列表

    FastMCP 要求工具函数有完整的类型化签名（不支持 **kwargs）。
    此函数根据 DB 中的 inputSchema 动态生成匹配的函数参数。

    来源: https://gofastmcp.com/servers/tools
    """
    params: list[inspect.Parameter] = []
    properties = (input_schema or {}).get("properties", {})
    required_fields = set((input_schema or {}).get("required", []))

    for param_name, param_info in properties.items():
        param_type = _json_type_to_python(param_info.get("type", "string"))
        is_required = param_name in required_fields

        if is_required:
            default = inspect.Parameter.empty
        else:
            default = param_info.get("default", None)

        params.append(
            inspect.Parameter(
                param_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=param_type,
            )
        )

    # Context 参数（FastMCP 自动注入）
    params.append(
        inspect.Parameter(
            "ctx",
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=None,
            annotation=Optional[Context],
        )
    )

    return params


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


# ══════════════════════════════════════════════════════════
#  _build_tool_wrapper — 工厂函数（签名生成 + 管道调度）
# ══════════════════════════════════════════════════════════
# 职责:
#   1. _build_params() 生成 inspect.Parameter 列表
#   2. 构建 inspect.Signature
#   3. 创建 tool_wrapper 闭合（管道调度: elicitation → execute → result）
#   4. 设置 __name__, __qualname__, __doc__, __signature__
#
# 注意: 签名生成必须在此函数内完成，FastMCP 不支持 **kwargs。
# 来源: https://gofastmcp.com/servers/tools ("Functions with **kwargs are not supported")


def _build_tool_wrapper(
    name: str,
    description: str,
    input_schema: dict,
    is_high_risk: bool,
    output_schema: dict | None = None,
) -> callable:
    """为 DB 驱动的工具创建类型化包装函数"""
    from app.agent.tool_registry import tool_registry

    # 管道调度
    async def tool_wrapper(**kwargs) -> dict:
        ctx = kwargs.pop("ctx", None)

        # Elicitation（高风险确认）
        if is_high_risk and ctx:
            elicit_result = await _handle_elicitation(ctx, name)
            if elicit_result:
                return ToolResultBuilder(
                    tool_name=name,
                    exec_result=elicit_result,
                    duration_ms=0,
                ).build()

        # 执行 + 进度
        exec_result, duration_ms = await _execute_tool(tool_registry, name, kwargs, ctx)

        # 结果构建（ToolResultBuilder 一次性处理所有规范字段）
        return ToolResultBuilder(
            tool_name=name,
            exec_result=exec_result,
            duration_ms=duration_ms,
            output_schema=output_schema,
        ).build()

    # ③ 函数元数据
    tool_wrapper.__name__ = name
    tool_wrapper.__qualname__ = name
    tool_wrapper.__doc__ = description

    return tool_wrapper


# ══════════════════════════════════════════════════════════
#  工具注册（全 DB 驱动）
# ══════════════════════════════════════════════════════════


async def register_tools_from_db(tool_registry) -> int:
    """从 ToolRegistry 加载所有启用的工具到 MCP Server

    FastMCP v3 add_tool 参数:
      - name, description: 工具标识
      - version: 组件版本号
      - timeout: 执行超时
      - title: 显示名称
      - output_schema: 输出 JSON Schema
      - annotations: ToolAnnotations 注解

    来源: https://gofastmcp.com/servers/tools
    """
    from app.core.database import AsyncSessionLocal
    from app.repository.tool_repo import ToolRepository

    repo = ToolRepository()
    async with AsyncSessionLocal() as db:
        tools = await repo.find_all(db, offset=0, limit=1000, enabled=1)

    count = 0
    for tool in tools:
        _register_mcp_tool(
            name=tool.name,
            description=tool.description,
            input_schema=tool.json_schema,
            output_schema=getattr(tool, 'output_schema', None),
            risk_level=getattr(tool, 'risk_level', 'low'),
            version=getattr(tool, 'version', None) or "1.0.0",
            timeout=getattr(tool, 'timeout_seconds', None) or 60,
            title=getattr(tool, 'display_name', None) or None,
            annotations=getattr(tool, 'annotations', None),
        )
        count += 1

    logger.info(f"MCP Server: 从 DB 加载 {count} 个工具")
    return count


def _register_mcp_tool(
    name: str,
    description: str,
    input_schema: dict,
    output_schema: dict | None = None,
    risk_level: str = "low",
    version: str = "1.0.0",
    timeout: int = 60,
    title: str | None = None,
    annotations: dict | None = None,
):
    """注册单个 MCP 工具（DB 元数据 + 动态签名 + annotations）"""
    is_high_risk = risk_level in ("high",)

    # 动态生成类型化包装函数（解决 **kwargs 问题）
    tool_func = _build_tool_wrapper(
        name=name,
        description=description,
        input_schema=input_schema,
        is_high_risk=is_high_risk,
        output_schema=output_schema,
    )

    # MCP 2025-06-18: Tool Annotations
    # DB 有精确值用精确值，没有则从 risk_level 推导兜底
    tool_annotations = ToolAnnotations.from_db(annotations, risk_level, title or name)
    mcp_annotations = MCPToolAnnotations(
        title=tool_annotations.title or None,
        readOnlyHint=tool_annotations.readOnlyHint,
        destructiveHint=tool_annotations.destructiveHint,
        idempotentHint=tool_annotations.idempotentHint,
        openWorldHint=tool_annotations.openWorldHint,
    )

    # FastMCP 3.4.2: 用 FunctionTool 构造函数直接传 input_schema 作为 parameters
    mcp_tool = MCPFunctionTool(
        fn=tool_func,
        name=name,
        description=description,
        parameters=input_schema,
        output_schema=output_schema if output_schema else None,
        annotations=mcp_annotations,
        version=version,
        timeout=float(timeout),
        title=title,
    )
    mcp_app.add_tool(mcp_tool)


# ══════════════════════════════════════════════════════════
#  Progress Tracking（长任务进度追踪）
# ══════════════════════════════════════════════════════════
# MCP 2025-06-18: 工具执行过程中可向 Client 推送进度
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


# ══════════════════════════════════════════════════════════
#  Sampling（服务端请求 Client 进行 LLM 推理）
# ══════════════════════════════════════════════════════════
# MCP 2025-06-18: Server 可请求 Client 执行 LLM 采样
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
        {"role": "assistant", "content": {"type": "text", "text": "..."}}
        或 {"error": "..."} 如果 Client 不支持 Sampling
    """
    try:
        result = await ctx.sample(
            messages=prompt,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            include_context=include_context,
        )
        text = result.text if hasattr(result, 'text') else str(result)
        return {"role": "assistant", "content": {"type": "text", "text": text or ""}}
    except Exception as e:
        logger.warning(f"Sampling 请求失败（Client 可能不支持）: {e}")
        return {"error": f"Sampling 不可用: {e}", "code": "SAMPLING_NOT_SUPPORTED"}


# ══════════════════════════════════════════════════════════
#  工具发现（cursor 分页）
# ══════════════════════════════════════════════════════════


@mcp_app.tool()
async def list_available_tools(cursor: str = "") -> dict:
    """列出所有可用的工具及其 MCP 元数据（inputSchema + outputSchema + annotations）。

    支持 cursor 分页（MCP 2025-06-18 规范）。
    """
    from app.agent.tool_registry import tool_registry

    all_tools = tool_registry.list_tools()
    page_size = 50

    offset = 0
    if cursor:
        try:
            offset = int(cursor)
        except (ValueError, TypeError):
            offset = 0

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
        # annotations 从 DB 加载，兜底从 risk_level 推导
        db_annotations = getattr(t, 'annotations', None)
        tool_annotations = ToolAnnotations.from_db(db_annotations, t.risk_level.value, t.display_name or t.name)
        tool_def["annotations"] = tool_annotations.to_dict()
        tools.append(tool_def)

    result = {
        "tools": tools,
        "count": len(tools),
        "protocol": "mcp",
        "version": "2025-06-18",
        "server": "beautiful-elf-tools",
    }

    if next_offset < len(all_tools):
        result["nextCursor"] = str(next_offset)

    return result


# ══════════════════════════════════════════════════════════
#  Resources（MCP 规范: 上下文数据）
# ══════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════
#  Prompts（MCP 规范: 预定义提示词模板）
# ══════════════════════════════════════════════════════════
# FastMCP v3: Prompt 返回 str 即可
# 来源: https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2


@mcp_app.prompt()
def chat_assistant() -> str:
    """通用对话助手提示词"""
    return (
        "你是主人的最强军师，能够使用工具回答用户问题。\n"
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


# ══════════════════════════════════════════════════════════
#  运行时热加载（listChanged 通知）
# ══════════════════════════════════════════════════════════


async def reload_tools(tool_registry) -> int:
    """运行时重新加载工具列表（DB 变更后调用）

    MCP 规范: 工具列表变更时发送 notifications/tools/list_changed
    FastMCP v3: add_tool() 会自动触发 listChanged 通知
    """
    from app.core.database import AsyncSessionLocal
    from app.repository.tool_repo import ToolRepository

    repo = ToolRepository()
    async with AsyncSessionLocal() as db:
        tools = await repo.find_all(db, offset=0, limit=1000, enabled=1)

    # 移除旧工具再重新注册，自动发送 listChanged 通知
    try:
        existing_names = {t.name for t in mcp_app._tool_manager.list_tools()}
    except AttributeError:
        existing_names = set()
    new_names = {tool.name for tool in tools}

    for name in existing_names - new_names:
        try:
            mcp_app.remove_tool(name)
            logger.info(f"[reload] 移除工具: {name}")
        except Exception:
            pass

    count = 0
    for tool in tools:
        _register_mcp_tool(
            name=tool.name,
            description=tool.description,
            input_schema=tool.json_schema,
            output_schema=getattr(tool, 'output_schema', None),
            risk_level=getattr(tool, 'risk_level', 'low'),
            version=getattr(tool, 'version', None) or "1.0.0",
            timeout=getattr(tool, 'timeout_seconds', None) or 60,
            title=getattr(tool, 'display_name', None) or None,
            annotations=getattr(tool, 'annotations', None),
        )
        count += 1

    logger.info(f"[reload] 工具热加载完成: {count} 个工具")
    return count


# ══════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════


async def init_mcp_server(tool_registry):
    """初始化 MCP Server（从 DB 加载工具）"""
    try:
        count = await register_tools_from_db(tool_registry)
        logger.info(f"MCP Server 初始化完成: {count} 个工具, Resources + Prompts 就绪")
    except Exception as e:
        logger.error(f"MCP Server 初始化失败: {e}")
        raise


def run_server(host: str = "0.0.0.0", port: int = 6880):
    """启动 MCP Server（Streamable HTTP 传输）

    来源: https://gofastmcp.com/getting-started/quickstart
    """
    logger.info(f"MCP Server 启动: {host}:{port} (Streamable HTTP)")
    mcp_app.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    from app.core.config import get_settings
    _settings = get_settings()
    run_server(_settings.MCP_SERVER_HOST, _settings.MCP_SERVER_PORT)
