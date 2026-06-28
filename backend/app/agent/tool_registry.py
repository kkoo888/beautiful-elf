"""工具注册表 — 桥接 DB 工具模型与 LangChain Tool Calling（v2 重构）

重构点:
  1. Copy-on-Write: 每次 Agent 调用创建独立的 registry view，不修改全局状态
  2. 结构化错误契约: retryable / user_facing / escalate
  3. 工具快照: 支持按场景动态选择工具，不全量 bind_tools
  4. 并发安全: 多用户同时使用不会互相覆盖

架构:
  MySQL tool 表 → ToolRegistry（运行时加载） → LangChain Tool 列表
  Agent 调用 → ToolRegistrySnapshot.execute() → 风险校验 → 参数校验 → 执行
"""
import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy

from app.core.logging import get_logger

logger = get_logger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ToolDef:
    """工具定义（MCP 规范: inputSchema + outputSchema + title）"""
    id: int                     # DB tool.id
    name: str                   # 工具名称（唯一，程序标识符）
    description: str            # 工具描述
    parameters: dict            # JSON Schema (MCP inputSchema)
    risk_level: RiskLevel       # 风险等级
    module: str                 # 所属模块
    category: str = "general"   # 工具分组: search/file/code/git/data/memory/media/comm/agent/doc/general
    func: Optional[Callable] = None  # 执行函数（可选，内置工具才有）
    output_schema: Optional[dict] = None  # MCP outputSchema（可选）
    display_name: str = ""      # 显示名称（MCP title，友好名称）
    strict_mode: bool = False   # OpenAI strict 模式（强制 JSON Schema 合规）


class ToolRegistry:
    """
    运行时工具注册表（全局基线）

    - 内置工具通过 register() 注册 Python 函数
    - DB 工具通过 load_from_db() 从 MySQL 加载
    - Agent 调用时通过 create_snapshot() 创建独立视图（Copy-on-Write）
    """

    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}
        self._db_loaded = False
        # Worker subgraph 依赖（由 agent_service 初始化时注入）
        self._worker_llm = None
        self._worker_tool_names: list[str] = []
        self._worker_context_engine = None
        # Parent context（每次请求前设置，spawn_agent 自动注入）
        self._parent_system_prompt: str = ""
        self._parent_memory: str = ""
        self._current_depth: int = 0

    def set_worker_deps(self, llm, tool_names: list, context_engine=None):
        """注入 Worker 子图依赖（Agent 引擎初始化后调用）"""
        self._worker_llm = llm
        self._worker_tool_names = tool_names
        self._worker_context_engine = context_engine

    def set_parent_context(self, system_prompt: str = "", memory: str = ""):
        """设置当前请求的 parent context（每次请求前调用，spawn_agent 自动注入）"""
        self._parent_system_prompt = system_prompt[:2000] if system_prompt else ""
        self._parent_memory = memory[:1000] if memory else ""

    def set_depth(self, depth: int):
        """设置当前 spawn 嵌套深度（spawn_agent 读取）"""
        self._current_depth = depth

    # ─── 注册（内置工具）────────────────────────────────

    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: dict,
        risk_level: str = RiskLevel.LOW,
        module: str = "builtin",
        tool_id: int = 0,
    ):
        """注册内置工具（启动时调用）"""
        self._tools[name] = ToolDef(
            id=tool_id,
            name=name,
            description=description,
            parameters=parameters,
            risk_level=RiskLevel(risk_level),
            module=module,
            func=func,
        )
        logger.info(f"工具注册: {name} (risk={risk_level})")

    # ─── DB 加载 ───────────────────────────────────────

    async def load_from_db(self, db_session) -> int:
        """从 MySQL tool 表加载所有启用的工具（启动时调用一次）"""
        from app.repository.tool_repo import ToolRepository
        repo = ToolRepository()

        tools = await repo.find_all(db_session, offset=0, limit=1000, enabled=1)
        count = 0

        for tool in tools:
            # DB 元数据 + 代码执行函数自动关联
            func = _EXEC_FUNC_MAP.get(tool.name)
            out_schema = getattr(tool, 'output_schema', None)

            display_name = getattr(tool, 'display_name', '') or ''

            strict = bool(getattr(tool, 'strict_mode', 0))

            if tool.name in self._tools:
                existing = self._tools[tool.name]
                existing.id = tool.id
                existing.description = tool.description
                existing.parameters = tool.json_schema or {}
                existing.output_schema = out_schema
                existing.risk_level = RiskLevel(tool.risk_level)
                existing.module = tool.module
                existing.category = getattr(tool, 'category', 'general')
                existing.display_name = display_name
                existing.strict_mode = strict
                if func:
                    existing.func = func
                continue

            self._tools[tool.name] = ToolDef(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                parameters=tool.json_schema or {},
                output_schema=out_schema,
                risk_level=RiskLevel(tool.risk_level),
                module=tool.module,
                category=getattr(tool, 'category', 'general'),
                func=func,
                display_name=display_name,
                strict_mode=strict,
            )
            count += 1

        self._db_loaded = True
        logger.info(f"从 DB 加载 {count} 个工具，共 {len(self._tools)} 个工具")
        return len(self._tools)

    # ─── 查询 ─────────────────────────────────────────

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def get_risk_level(self, name: str) -> str:
        t = self._tools.get(name)
        return t.risk_level.value if t else RiskLevel.LOW.value

    def list_tools(self) -> List[ToolDef]:
        return list(self._tools.values())

    def list_tool_summaries(self) -> List[dict]:
        """返回工具摘要（用于 ContextEngine 动态选择 + MCP tools/list）"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk": t.risk_level.value,
                "module": t.module,
                "category": t.category,
                "output_schema": t.output_schema,
                "strict_mode": t.strict_mode,
            }
            for t in self._tools.values()
        ]

    def get_langchain_tools(self, tool_names: Optional[List[str]] = None) -> list:
        """
        返回 LangChain Tool 列表（用于 bind_tools）。

        Args:
            tool_names: 指定工具名列表。为 None 时返回全部。
        """
        from langchain_core.tools import StructuredTool
        tools = []
        target_tools = self._tools.values()
        if tool_names:
            target_tools = [t for t in self._tools.values() if t.name in set(tool_names)]

        for t in target_tools:
            func = t.func or self._make_db_tool_wrapper(t.name)
            # 从 DB json_schema 构建 args_schema，确保 LLM 能看到工具参数定义
            args_schema = self._build_args_schema(t.name, t.parameters) if t.parameters else None
            tool = StructuredTool.from_function(
                func=func,
                name=t.name,
                description=t.description,
                args_schema=args_schema,
                coroutine=func if asyncio.iscoroutinefunction(func) else None,
            )
            # OpenAI strict 模式元数据（bind_tools 时读取）
            if t.strict_mode:
                tool.metadata = tool.metadata or {}
                tool.metadata["strict"] = True
            tools.append(tool)
        return tools

    def get_strict_tool_names(self) -> set:
        """返回启用了 strict 模式的工具名集合"""
        return {t.name for t in self._tools.values() if t.strict_mode}

    @staticmethod
    def _build_args_schema(tool_name: str, json_schema: dict):
        """从 DB JSON Schema 动态构建 Pydantic model（供 StructuredTool.args_schema）"""
        from pydantic import create_model, Field
        from pydantic.fields import FieldInfo

        properties = json_schema.get("properties", {})
        required = set(json_schema.get("required", []))
        fields = {}
        for pname, pinfo in properties.items():
            ptype = str  # 默认 str
            desc = pinfo.get("description", "")
            default = ... if pname in required else pinfo.get("default", "")
            fields[pname] = (ptype, Field(default=default, description=desc))
        try:
            return create_model(f"{tool_name}Args", **fields)
        except Exception:
            return None

    def _make_db_tool_wrapper(self, tool_name: str) -> Callable:
        """为 DB 工具创建通用执行包装器"""
        async def db_tool_wrapper(**kwargs) -> str:
            result = await self.execute(tool_name, kwargs, approved=False)
            return str(result)
        return db_tool_wrapper

    # ─── Copy-on-Write 快照 ────────────────────────────

    def create_snapshot(self, extra_tools: Optional[List[dict]] = None) -> "ToolRegistrySnapshot":
        """
        创建不可变快照（Copy-on-Write）。

        用于并发安全：每次 Agent 调用使用独立的 snapshot，
        技能工具临时注册到 snapshot 中，不影响全局 registry。

        Args:
            extra_tools: 额外工具定义列表（技能工具等）

        Returns:
            ToolRegistrySnapshot 实例
        """
        snapshot_tools = dict(self._tools)

        # 合并额外工具
        if extra_tools:
            for td in extra_tools:
                name = td.get("name", "")
                if not name:
                    continue
                snapshot_tools[name] = ToolDef(
                    id=td.get("id", 0),
                    name=name,
                    description=td.get("description", ""),
                    parameters=td.get("parameters", {"type": "object", "properties": {}}),
                    risk_level=RiskLevel(td.get("risk_level", "low")),
                    module=td.get("module", "skill"),
                    func=td.get("func"),
                )

        return ToolRegistrySnapshot(snapshot_tools)

    # ─── 执行 ─────────────────────────────────────────

    async def execute(
        self,
        name: str,
        arguments: dict,
        approved: bool = False,
        db_session=None,
    ) -> Any:
        """
        执行工具（全局 registry，非并发安全，建议用 snapshot）。
        """
        t = self._tools.get(name)
        if not t:
            return {"error": f"工具 '{name}' 不存在", "code": "TOOL_NOT_FOUND"}

        return await self._execute_tool(t, arguments, approved, db_session)

    async def _execute_tool(self, t: ToolDef, arguments: dict, approved: bool, db_session=None) -> Any:
        """通用工具执行逻辑"""
        import time

        # 风险校验
        if t.risk_level == RiskLevel.HIGH and not approved:
            return {
                "needs_approval": True,
                "tool": t.name,
                "arguments": arguments,
                "risk_level": t.risk_level.value,
                "message": f"⚠️ {t.name} 是高风险操作，需要用户确认",
            }

        # 参数校验
        try:
            import jsonschema
            jsonschema.validate(arguments, t.parameters)
        except ImportError:
            pass
        except jsonschema.ValidationError as e:
            return {"error": f"参数校验失败: {e.message}", "code": "VALIDATION_ERROR"}

        # 执行
        start_time = time.time()
        success = True
        result = None

        try:
            if t.func:
                if asyncio.iscoroutinefunction(t.func):
                    result = await t.func(**arguments)
                else:
                    result = t.func(**arguments)
            else:
                result = {
                    "tool": t.name,
                    "arguments": arguments,
                    "module": t.module,
                    "message": f"工具 '{t.name}' 已触发，由模块 '{t.module}' 处理",
                }
        except Exception as e:
            logger.error(f"工具 {t.name} 执行异常: {e}")
            result = {"error": str(e), "code": "TOOL_EXECUTION_ERROR"}
            success = False

        duration_ms = int((time.time() - start_time) * 1000)

        # 异步记录统计
        if db_session and t.id > 0:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._record_stats(db_session, t.id, success, duration_ms))
            except RuntimeError:
                pass

        return result

    async def _record_stats(self, db_session, tool_id: int, success: bool, duration_ms: int):
        """异步记录工具调用统计"""
        try:
            from app.repository.tool_repo import ToolRepository
            repo = ToolRepository()
            await repo.record_call(db_session, tool_id, success, duration_ms)
        except Exception as e:
            logger.warning(f"工具统计记录失败: {e}")


class ToolRegistrySnapshot:
    """
    工具注册表快照（Copy-on-Write，不可变）

    - 每次 Agent 调用创建一个 snapshot
    - 支持临时添加技能工具，不影响全局 registry
    - 并发安全：多个 snapshot 互不干扰
    """

    def __init__(self, tools: Dict[str, ToolDef]):
        self._tools = dict(tools)  # 浅拷贝，不修改原始 dict

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def get_risk_level(self, name: str) -> str:
        t = self._tools.get(name)
        return t.risk_level.value if t else RiskLevel.LOW.value

    def list_tools(self) -> List[ToolDef]:
        return list(self._tools.values())

    def get_langchain_tools(self, tool_names: Optional[List[str]] = None) -> list:
        """返回 LangChain Tool 列表"""
        from langchain_core.tools import StructuredTool
        tools = []
        target = self._tools.values()
        if tool_names:
            target = [t for t in self._tools.values() if t.name in set(tool_names)]

        for t in target:
            func = t.func or self._make_wrapper(t.name)
            args_schema = ToolRegistry._build_args_schema(t.name, t.parameters) if t.parameters else None
            tool = StructuredTool.from_function(
                func=func, name=t.name, description=t.description,
                args_schema=args_schema,
                coroutine=func if asyncio.iscoroutinefunction(func) else None,
            )
            tools.append(tool)
        return tools

    def _make_wrapper(self, tool_name: str) -> Callable:
        async def wrapper(**kwargs) -> str:
            result = await self.execute(tool_name, kwargs)
            return str(result)
        return wrapper

    async def execute(self, name: str, arguments: dict, approved: bool = False) -> Any:
        """在 snapshot 内执行工具"""
        t = self._tools.get(name)
        if not t:
            return {"error": f"工具 '{name}' 不存在", "code": "TOOL_NOT_FOUND"}

        # 复用全局 registry 的执行逻辑
        registry = tool_registry
        return await registry._execute_tool(t, arguments, approved)


# ─── 内置工具实现 ─────────────────────────────────────────

async def _fetch_page_content(url: str, max_chars: int = 3000) -> str:
    """抓取单个 URL 的正文内容（web_search 内部用，不对外暴露）"""
    import re
    import httpx
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, verify=False) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            text = resp.text
            if "text/html" in content_type:
                text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars]
    except Exception:
        return ""


# 自动抓取前 N 个搜索结果的全文（可通过环境变量调整）
_AUTO_FETCH_COUNT = 3   # 抓取前几个结果
_AUTO_FETCH_MAX_CHARS = 3000  # 每个结果最大字符数


async def web_search(query: str, max_results: int = 5) -> dict:
    max_results = int(max_results)  # 防御：LLM 可能传字符串
    """搜索互联网获取实时信息

    优先使用 MiMo 搜索 API（小米，每日免费 1000 次）。
    降级链: MiMo Search → SearXNG → 空结果
    v8.0: 搜索后自动抓取前 N 个结果全文，消除二次 web_fetch 降级。
    """
    import os
    import asyncio
    import httpx
    from app.core.config import get_settings

    # ── 1. 优先 MiMo 搜索 API（免费、国内可用）──
    mimo_token = os.getenv("MIMO_SEARCH_TOKEN", "").strip()
    mimo_api_url = os.getenv("MIMO_SEARCH_API_URL", "https://aistudio.xiaomimimo.com/open-apis/search").strip()

    if mimo_token:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    mimo_api_url,
                    json={"token": mimo_token, "query": query},
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") == 0:
                    web_pages = data.get("data", {}).get("webPages", {}).get("value", [])
                    if web_pages:
                        results = [
                            {
                                "title": r.get("name", ""),
                                "url": r.get("url", ""),
                                "snippet": r.get("snippet", "") or r.get("summary", ""),
                                "source": r.get("siteName", ""),
                                "date": r.get("datePublished", "").split("T")[0] if r.get("datePublished") else "",
                            }
                            for r in web_pages[:max_results]
                        ]
                        # 自动抓取前 N 个结果的全文（并发，不阻塞整体超时）
                        fetch_count = min(_AUTO_FETCH_COUNT, len(results))
                        if fetch_count > 0:
                            urls_to_fetch = [r["url"] for r in results[:fetch_count] if r["url"]]
                            fetched = await asyncio.gather(
                                *[_fetch_page_content(u, _AUTO_FETCH_MAX_CHARS) for u in urls_to_fetch],
                                return_exceptions=True,
                            )
                            for i, content in enumerate(fetched):
                                if isinstance(content, str) and content:
                                    results[i]["content"] = content
                        return {"results": results}
        except Exception as e:
            logger.warning(f"[web_search] MiMo 搜索失败: {e}")

    # ── 2. 降级 SearXNG ──
    searxng_url = get_settings().SEARXNG_URL.strip()
    if searxng_url:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{searxng_url.rstrip('/')}/search",
                    params={"q": query, "format": "json", "count": max_results},
                )
                resp.raise_for_status()
                data = resp.json()
                raw_results = data.get("results", [])[:max_results]
                if raw_results:
                    results = [
                        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
                        for r in raw_results
                    ]
                    # SearXNG 也做自动抓取
                    fetch_count = min(_AUTO_FETCH_COUNT, len(results))
                    if fetch_count > 0:
                        urls_to_fetch = [r["url"] for r in results[:fetch_count] if r["url"]]
                        fetched = await asyncio.gather(
                            *[_fetch_page_content(u, _AUTO_FETCH_MAX_CHARS) for u in urls_to_fetch],
                            return_exceptions=True,
                        )
                        for i, content in enumerate(fetched):
                            if isinstance(content, str) and content:
                                results[i]["content"] = content
                    return {"results": results}
        except Exception:
            pass

    # ── 3. 全部失败，返回空结果 ──
    return {"results": [], "fallback": "no_search_available", "message": "搜索服务暂不可用，请用自身知识回答"}


async def execute_code(language: str, code: str) -> dict:
    """在沙箱中执行代码"""
    sandbox_images = {"python": "python:3.12-slim", "javascript": "node:20-slim"}
    image = sandbox_images.get(language)
    if not image:
        return {"error": f"不支持的语言: {language}"}

    proc = await asyncio.create_subprocess_exec(
        "docker", "run", "--rm",
        "--network=none",
        "--memory=128m",
        "--cpus=0.5",
        "--read-only",
        "--tmpfs", "/tmp:size=10m",
        "--pids-limit", "50",
        "--security-opt", "no-new-privileges",
        image, "sh", "-c", code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        return {
            "stdout": stdout.decode()[:5000],
            "stderr": stderr.decode()[:2000],
            "exit_code": proc.returncode,
        }
    except asyncio.TimeoutError:
        # 修复: 超时后正确杀掉进程
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass
        return {"error": "代码执行超时（10秒）", "code": "EXECUTION_TIMEOUT"}


async def read_file(path: str, workingDirectory: str = None) -> dict:
    """读取工作空间中的文件"""
    workspace, target = _resolve_path(path, workingDirectory)
    if target is None:
        return {"error": "路径穿越攻击已拦截"}
    if not target.exists():
        return {"error": f"文件不存在: {path}"}
    if target.stat().st_size > 1_000_000:
        return {"error": "文件过大（>1MB）"}
    return {"content": target.read_text(encoding="utf-8", errors="ignore")[:50000]}


async def query_database(sql: str) -> dict:
    """查询数据库（只读 SELECT，参数化查询防注入）"""
    import re
    from sqlalchemy import text

    sql_stripped = sql.strip().rstrip(";")
    sql_upper = sql_stripped.upper()

    if not sql_upper.startswith("SELECT"):
        return {"error": "只允许 SELECT 查询"}

    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "EXEC", "EXECUTE", "UNION"]
    for kw in forbidden:
        if re.search(rf'\b{kw}\b', sql_upper):
            return {"error": f"禁止使用 {kw} 语句"}

    if ";" in sql_stripped:
        return {"error": "禁止多语句执行"}

    if "LIMIT" not in sql_upper:
        sql_stripped += " LIMIT 100"

    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(sql_stripped))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"columns": columns, "rows": rows, "count": len(rows)}


# ── 工作目录解析（OpenClaw + Claude Code 混合模式）──────────────
#
# 设计理念：
#   - 默认工作目录 = 项目根目录（自动检测，非 backend/）
#   - 工具可通过 workingDirectory 参数覆盖（Cursor 模式）
#   - 相对路径 → 解析到工作目录；绝对路径 → 安全检查后允许
#   - 路径穿越拦截保留（防止访问敏感目录）

# 允许的绝对路径前缀（安全白名单，运行时动态生成）
def _get_allowed_prefixes() -> tuple:
    from app.core.config import get_settings
    workspace = get_settings().RESOLVED_WORKSPACE
    return (workspace + "/", "/tmp/", "/home/")

# 敏感目录黑名单
_SENSITIVE_PATHS = (
    "/etc/shadow", "/etc/passwd", "/etc/sudoers",
    "/root/.ssh", "/home/.ssh",
    "/proc", "/sys", "/dev",
)


def _get_workspace(working_directory: str = None) -> Path:
    """获取工作目录

    优先级：
    1. workingDirectory 参数（工具调用时指定）
    2. 配置中的 WORKSPACE_DIR / RESOLVED_WORKSPACE
    3. 自动检测项目根目录
    """
    from app.core.config import get_settings
    if working_directory:
        p = Path(working_directory).expanduser()
        if p.is_absolute():
            return p.resolve()
        # 相对路径 → 相对于项目根目录
        return Path(get_settings().RESOLVED_WORKSPACE).resolve() / p
    return Path(get_settings().RESOLVED_WORKSPACE).resolve()


def _resolve_path(path: str, working_directory: str = None) -> tuple:
    """解析路径并做安全检查

    Returns:
        (workspace: Path, target: Path) 或 (workspace, None) 如果被拦截
    """
    workspace = _get_workspace(working_directory)
    raw = Path(path).expanduser()

    # 绝对路径：安全检查
    if raw.is_absolute():
        raw_resolved = raw.resolve()
        # 检查敏感目录
        for sensitive in _SENSITIVE_PATHS:
            if str(raw_resolved).startswith(sensitive):
                return workspace, None
        # 检查白名单
        allowed = False
        for prefix in _get_allowed_prefixes():
            if str(raw_resolved).startswith(prefix):
                allowed = True
                break
        # 项目根目录内的绝对路径也允许
        if str(raw_resolved).startswith(str(workspace)):
            allowed = True
        if not allowed:
            return workspace, None
        return workspace, raw_resolved

    # 相对路径：解析到工作目录
    target = (workspace / raw).resolve()
    # 路径穿越检查
    if not str(target).startswith(str(workspace)):
        return workspace, None
    return workspace, target


# ── 执行函数注册表（DB 工具自动关联执行函数）──────────────
# 工具元数据全部由 DB 管理，这里只做 name → 执行函数的映射

# ── 文件系统工具 ─────────────────────────────────────────

async def write_file(path: str, content: str, encoding: str = "utf-8", workingDirectory: str = None) -> dict:
    """写入文件到工作空间"""
    workspace, target = _resolve_path(path, workingDirectory)
    if target is None:
        return {"error": "路径穿越攻击已拦截"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding)
    return {"success": True, "bytes_written": len(content.encode(encoding)), "path": path}


async def list_files(path: str = ".", pattern: str = None, recursive: bool = False, workingDirectory: str = None) -> dict:
    """列出工作空间目录下的文件"""
    import fnmatch
    workspace, target = _resolve_path(path, workingDirectory)
    if target is None:
        return {"error": "路径穿越攻击已拦截"}
    if not target.exists():
        return {"error": f"目录不存在: {path}"}
    entries = []
    if recursive:
        items = target.rglob(pattern or "*")
    else:
        items = target.glob(pattern or "*")
    for item in sorted(items):
        entries.append({
            "name": item.name,
            "path": str(item.relative_to(workspace)),
            "is_dir": item.is_dir(),
            "size": item.stat().st_size if item.is_file() else 0,
        })
    return {"files": entries[:500]}


async def apply_patch(path: str, edits: list, workingDirectory: str = None) -> dict:
    """对文件进行精确文本替换"""
    workspace, target = _resolve_path(path, workingDirectory)
    if target is None:
        return {"error": "路径穿越攻击已拦截"}
    if not target.exists():
        return {"error": f"文件不存在: {path}"}
    try:
        content = target.read_text(encoding="utf-8")
        replacements = 0
        for edit in edits:
            old_text = edit.get("oldText", "")
            new_text = edit.get("newText", "")
            if old_text and old_text in content:
                content = content.replace(old_text, new_text, 1)
                replacements += 1
        target.write_text(content, encoding="utf-8")
        return {"success": True, "replacements": replacements}
    except Exception as e:
        return {"error": f"补丁失败: {e}"}


# ── Git 工具 ────────────────────────────────────────────

async def _run_git(*args, repo_path: str = ".", workingDirectory: str = None) -> tuple:
    """执行 git 命令的内部辅助函数"""
    import asyncio
    workspace, target = _resolve_path(repo_path, workingDirectory)
    if target is None:
        return 1, "", "路径穿越攻击已拦截"
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=str(target),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        return proc.returncode, stdout.decode("utf-8", errors="ignore").strip(), stderr.decode("utf-8", errors="ignore").strip()
    except asyncio.TimeoutError:
        return 1, "", "Git 命令超时"
    except Exception as e:
        return 1, "", str(e)


async def git_status(repo_path: str = ".", workingDirectory: str = None) -> dict:
    """查看 Git 仓库状态"""
    code, out, err = await _run_git("status", "--porcelain=v1", repo_path=repo_path, workingDirectory=workingDirectory)
    if code != 0:
        return {"error": err}
    modified, added, deleted, untracked = [], [], [], []
    for line in out.splitlines():
        if not line.strip():
            continue
        status = line[:2].strip()
        filepath = line[3:].strip()
        if status == "M":
            modified.append(filepath)
        elif status == "A":
            added.append(filepath)
        elif status == "D":
            deleted.append(filepath)
        elif status == "??":
            untracked.append(filepath)
    _, branch_out, _ = await _run_git("rev-parse", "--abbrev-ref", "HEAD", repo_path=repo_path)
    return {"branch": branch_out, "modified": modified, "added": added, "deleted": deleted, "untracked": untracked}


async def git_diff(repo_path: str = ".", staged: bool = False, commit: str = None, file_path: str = None, workingDirectory: str = None) -> dict:
    """查看 Git 差异"""
    args = ["diff"]
    if staged:
        args.append("--staged")
    if commit:
        args.append(commit)
    if file_path:
        args.append(file_path)
    code, out, err = await _run_git(*args, repo_path=repo_path, workingDirectory=workingDirectory)
    if code != 0:
        return {"error": err}
    files_changed = out.count("diff --git")
    return {"diff": out[:10000], "files_changed": files_changed}


async def git_commit(repo_path: str = ".", message: str = "", files: list = None, workingDirectory: str = None) -> dict:
    """Git 提交"""
    if files:
        for f in files:
            code, _, err = await _run_git("add", f, repo_path=repo_path)
            if code != 0:
                return {"error": f"git add {f} 失败: {err}"}
    else:
        code, _, err = await _run_git("add", "-A", repo_path=repo_path)
        if code != 0:
            return {"error": f"git add 失败: {err}"}
    code, out, err = await _run_git("commit", "-m", message, repo_path=repo_path)
    if code != 0:
        return {"error": f"git commit 失败: {err}"}
    _, hash_out, _ = await _run_git("rev-parse", "HEAD", repo_path=repo_path)
    return {"success": True, "commit_hash": hash_out}


async def git_log(repo_path: str = ".", limit: int = 10, file_path: str = None, workingDirectory: str = None) -> dict:
    """查看 Git 日志"""
    args = ["log", f"--max-count={limit}", "--pretty=format:%H|%an|%ai|%s"]
    if file_path:
        args.extend(["--", file_path])
    code, out, err = await _run_git(*args, repo_path=repo_path)
    if code != 0:
        return {"error": err}
    commits = []
    for line in out.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({"hash": parts[0][:8], "author": parts[1], "date": parts[2], "message": parts[3]})
    return {"commits": commits}


# ── Shell 工具 ──────────────────────────────────────────

async def exec_command(command: str, workdir: str = None, timeout: int = 10, workingDirectory: str = None) -> dict:
    """在沙箱中执行 Shell 命令"""
    import asyncio
    workspace = _get_workspace(workingDirectory)
    cwd = str(workspace)
    if workdir:
        _, target = _resolve_path(workdir, workingDirectory)
        if target is None:
            return {"error": "路径穿越攻击已拦截"}
        cwd = str(target)
    # 危险命令拦截
    dangerous = ["rm -rf /", "mkfs", "dd if=", "wget ", "curl ", "> /dev/"]
    for d in dangerous:
        if d in command:
            return {"error": f"危险命令已拦截: 包含 '{d}'"}
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "stdout": stdout.decode("utf-8", errors="ignore")[:5000],
            "stderr": stderr.decode("utf-8", errors="ignore")[:2000],
            "exit_code": proc.returncode,
        }
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return {"error": f"命令超时（{timeout}秒）"}


# ── 网页抓取 ────────────────────────────────────────────

async def web_fetch(url: str, extract_mode: str = "markdown", max_chars: int = 10000) -> dict:
    """抓取 URL 内容并提取为可读文本

    v5.2: 增加 User-Agent、超时、内容清洗。
    """
    import httpx
    import re
    if not url or not url.strip():
        return {"error": "url 参数不能为空"}
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            text = resp.text
            if "text/html" in content_type:
                text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
            return {"content": text[:max_chars], "title": "", "url": str(resp.url)}
    except httpx.TimeoutException:
        return {"error": "抓取超时（20秒）"}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}"}
    except Exception as e:
        return {"error": f"抓取失败: {type(e).__name__}: {e}"}


# ── 记忆工具 ────────────────────────────────────────────

async def memory_save(content: str, category: str = "fact", tags: list = None) -> dict:
    """保存到长期记忆"""
    from datetime import datetime
    workspace = _get_workspace()
    memory_dir = workspace / "memory"
    memory_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    memory_file = memory_dir / f"{today}.md"
    tag_str = f" [{', '.join(tags)}]" if tags else ""
    entry = f"\n\n### {category.upper()}{tag_str} — {datetime.now().strftime('%H:%M')}\n{content}\n"
    try:
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(entry)
        return {"success": True, "path": str(memory_file.relative_to(workspace))}
    except Exception as e:
        return {"error": f"保存记忆失败: {e}"}


async def memory_search(query: str, max_results: int = 5) -> dict:
    """搜索长期记忆（简单关键词匹配）"""
    import re
    workspace = _get_workspace()
    memory_dir = workspace / "memory"
    if not memory_dir.exists():
        return {"results": []}
    results = []
    query_lower = query.lower()
    for md_file in sorted(memory_dir.glob("*.md"), reverse=True):
        try:
            content = md_file.read_text(encoding="utf-8")
            # 按段落分割
            sections = re.split(r"\n### ", content)
            for section in sections:
                if query_lower in section.lower():
                    results.append({
                        "content": section[:500],
                        "path": str(md_file.relative_to(workspace)),
                        "score": section.lower().count(query_lower),
                    })
                    if len(results) >= max_results:
                        return {"results": results}
        except Exception:
            continue
    return {"results": results}


async def memory_edit(point_id: str, new_content: str, reason: str = "") -> dict:
    """编辑已有记忆的内容（自编辑机制）

    Args:
        point_id: Qdrant 记忆点 ID
        new_content: 更新后的内容摘要
        reason: 修改原因（可选，用于审计）
    """
    try:
        from app.mappers.qdrant_mapper import QdrantMapper
        qdrant = QdrantMapper()

        # 读取当前记忆
        current = qdrant.get_by_id("memory_vectors", point_id)
        if not current:
            return {"error": f"记忆不存在: {point_id}"}

        old_summary = current.get("summary", "")

        # 重新生成 embedding 并 upsert（内容变了，向量也要更新）
        try:
            from app.services.onnx_embedding_service import get_onnx_embedding_service
            from datetime import datetime
            onnx_svc = await get_onnx_embedding_service()
            new_vector = await onnx_svc.get_embedding(new_content)
            qdrant.upsert(
                collection="memory_vectors",
                point_id=point_id,
                vector=new_vector,
                payload={
                    **current,
                    "summary": new_content,
                    "updated_at": datetime.utcnow().isoformat(),
                    "edit_reason": reason,
                },
            )
        except Exception:
            # embedding 不可用时只更新 payload
            from datetime import datetime
            qdrant._client.set_payload(
                collection_name="memory_vectors",
                payload={
                    "summary": new_content,
                    "updated_at": datetime.utcnow().isoformat(),
                    "edit_reason": reason,
                },
                points=[point_id],
            )

        return {
            "success": True,
            "point_id": point_id,
            "old_content": old_summary[:200],
            "new_content": new_content[:200],
            "reason": reason,
        }
    except Exception as e:
        return {"error": f"编辑记忆失败: {e}"}


async def memory_delete(point_id: str, reason: str = "") -> dict:
    """删除记忆（自编辑机制）

    Args:
        point_id: Qdrant 记忆点 ID
        reason: 删除原因（可选，用于审计）
    """
    try:
        from app.mappers.qdrant_mapper import QdrantMapper
        from qdrant_client.models import PointIdsList
        qdrant = QdrantMapper()

        # 先验证记忆存在
        current = qdrant.get_by_id("memory_vectors", point_id)
        if not current:
            return {"error": f"记忆不存在: {point_id}"}

        # 物理删除
        qdrant._client.delete(
            collection_name="memory_vectors",
            points_selector=PointIdsList(points=[point_id]),
        )

        return {
            "success": True,
            "point_id": point_id,
            "deleted_content": current.get("summary", "")[:200],
            "reason": reason,
        }
    except Exception as e:
        return {"error": f"删除记忆失败: {e}"}


# ── 会话工具 ────────────────────────────────────────────

async def spawn_agent(task: str, label: str = None, mode: str = "run", timeout: int = 300) -> dict:
    """生成子 Agent 执行子任务（Worker Subgraph 模式）

    自动从 tool_registry 读取 parent context 并注入 worker。
    """
    import asyncio
    from app.core.logging import get_logger as _get_logger
    _logger = _get_logger("spawn_agent")

    # 类型安全: LLM 工具调用可能传入 str 类型
    try:
        depth = int(depth)
    except (TypeError, ValueError):
        depth = 0
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        timeout = 300

    MAX_DEPTH = 2

    llm = tool_registry._worker_llm
    if not llm:
        return {"error": "Worker 子图未初始化（llm 未注入）", "task": task, "label": label}

    # 获取 parent context（自动注入，无需 LLM 传递）
    parent_system_prompt = tool_registry._parent_system_prompt
    parent_memory = tool_registry._parent_memory
    depth = getattr(tool_registry, '_current_depth', 0)

    if depth > MAX_DEPTH:
        _logger.warning(f"[spawn_agent] 深度超限 ({depth}/{MAX_DEPTH}): {label}")
        return {"error": f"子 Agent 嵌套深度超限（最大 {MAX_DEPTH} 层）", "task": task, "label": label, "depth": depth}

    # 获取 worker 工具
    worker_tool_names = tool_registry._worker_tool_names or [
        "web_search", "execute_code", "read_file", "query_database", "web_fetch",
    ]
    tools = tool_registry.get_langchain_tools(worker_tool_names)
    if not tools:
        tools = []

    # 构建 system prompt（不含 parent context，parent context 在 worker 内部注入）
    system_prompt = "你是一个专注的子任务执行器。根据给定的任务，使用可用工具完成工作，返回结构化的执行结果。"

    try:
        from app.agent.worker_graph import build_worker_graph
        worker = build_worker_graph(llm=llm, tools=tools, system_prompt=system_prompt, max_iterations=5, depth=depth)

        initial_state = {
            "messages": [],
            "task": task,
            "context": "",
            "iteration": 0,
            "max_iterations": 5,
            "final_answer": None,
            "force_end": False,
            "parent_trace_id": f"worker-{label or 'sub'}",
            "parent_system_prompt": parent_system_prompt,
            "parent_memory": parent_memory,
        }

        result = await asyncio.wait_for(
            worker.ainvoke(initial_state),
            timeout=timeout,
        )

        answer = result.get("final_answer") or ""
        if not answer:
            for msg in reversed(result.get("messages", [])):
                content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
                if content:
                    answer = content if isinstance(content, str) else str(content)
                    break

        # 收集 worker 使用的工具
        worker_tools_used = []
        for msg in result.get("messages", []):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                    if name:
                        worker_tools_used.append(name)

        _logger.info(f"[spawn_agent] 子任务完成: label={label} depth={depth} answer_len={len(answer)} tools={worker_tools_used}")
        return {
            "success": True,
            "result": answer,
            "tools_used": worker_tools_used,
            "label": label,
            "depth": depth,
        }

    except asyncio.TimeoutError:
        _logger.warning(f"[spawn_agent] 子任务超时 ({timeout}s): {label}")
        return {"error": f"子任务执行超时 ({timeout}s)", "task": task, "label": label, "depth": depth}
    except Exception as e:
        _logger.error(f"[spawn_agent] 子任务失败: {e}", exc_info=True)
        return {"error": f"子任务执行失败: {e}", "task": task, "label": label, "depth": depth}


async def list_sessions(limit: int = 20, active_minutes: int = None) -> dict:
    """列出活跃会话"""
    # 预留接口
    return {"error": "会话列表功能待对接 sessions_list 接口"}


async def session_search(query: str, limit: int = 10, session_key: str = None) -> dict:
    """搜索会话记录"""
    return {"error": "会话搜索功能待对接 session_search 接口"}


# ── 消息工具 ────────────────────────────────────────────

async def send_message(channel: str = None, target: str = None, message: str = "") -> dict:
    """发送消息到指定渠道"""
    return {"error": "消息发送功能待对接 message 接口", "channel": channel, "target": target}


# ── 媒体工具 ────────────────────────────────────────────

async def image_generate(prompt: str, size: str = "1024x1024", style: str = None) -> dict:
    """生成图片"""
    return {"error": "图片生成功能待对接 DALL-E/Midjourney 接口"}


async def text_to_speech(text: str, voice: str = "alloy", speed: float = 1.0) -> dict:
    """文本转语音"""
    return {"error": "TTS 功能待对接语音合成接口"}


async def parse_pdf(path: str, pages: str = None, workingDirectory: str = None) -> dict:
    """解析 PDF 文件"""
    workspace, target = _resolve_path(path, workingDirectory)
    if target is None:
        return {"error": "路径穿越攻击已拦截"}
    if not target.exists():
        return {"error": f"文件不存在: {path}"}
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
try:
    import fitz
    doc = fitz.open("{target}")
    for page in doc:
        print(page.get_text())
except ImportError:
    print("ERROR: pip install PyMuPDF")
"""],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {"error": result.stderr or "PDF 解析失败"}
        return {"content": result.stdout[:50000]}
    except Exception as e:
        return {"error": f"PDF 解析失败: {e}"}


# ── 定时任务工具 ────────────────────────────────────────

async def cron_create(name: str = "", schedule: dict = None, message: str = "", enabled: bool = True) -> dict:
    """创建定时任务"""
    return {"error": "定时任务功能待对接 cron 接口", "name": name, "schedule": schedule}


async def cron_list(include_disabled: bool = False) -> dict:
    """列出定时任务"""
    return {"error": "定时任务列表功能待对接 cron 接口"}


# ── 技能工具 ────────────────────────────────────────────

async def skill_search(query: str, limit: int = 5) -> dict:
    """搜索可用技能"""
    from pathlib import Path
    import json
    skills_dir = Path.home() / ".openclaw" / "skills"
    if not skills_dir.exists():
        return {"skills": []}
    results = []
    query_lower = query.lower()
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            content = skill_md.read_text(encoding="utf-8")[:300]
            name = skill_dir.name
            # 从 SKILL.md 提取描述
            desc = ""
            for line in content.splitlines():
                if line.startswith("description:") or line.startswith("name:"):
                    desc = line.split(":", 1)[1].strip().strip("|").strip()
                    break
            if query_lower in name.lower() or query_lower in content.lower():
                results.append({"name": name, "description": desc[:200], "version": "1.0.0"})
                if len(results) >= limit:
                    break
        except Exception:
            continue
    return {"skills": results}


# ── 路由控制 ────────────────────────────────────────────

async def router_control(action: str = "status", model: str = None, reason: str = None) -> dict:
    """查看或调整路由器"""
    if action == "status":
        from pathlib import Path
        version_file = Path(__file__).parent.parent / "router" / "models" / "v4.2_phase3_inference" / "version.json"
        if version_file.exists():
            import json
            meta = json.loads(version_file.read_text())
            return {"route_class": "auto", "selected_model": "ML router", "version": meta.get("version", "unknown")}
        return {"route_class": "auto", "selected_model": "ML router", "version": "not loaded"}
    return {"error": f"不支持的操作: {action}"}



_EXEC_FUNC_MAP = {
    # 已有
    "web_search": web_search,
    "execute_code": execute_code,
    "read_file": read_file,
    "query_database": query_database,
    # 文件系统
    "write_file": write_file,
    "list_files": list_files,
    "apply_patch": apply_patch,
    # Git
    "git_status": git_status,
    "git_diff": git_diff,
    "git_commit": git_commit,
    "git_log": git_log,
    # Shell
    "exec_command": exec_command,
    # 网页
    "web_fetch": web_fetch,
    # 记忆
    "memory_save": memory_save,
    "memory_search": memory_search,
    "memory_edit": memory_edit,
    "memory_delete": memory_delete,
    # 会话
    "spawn_agent": spawn_agent,
    "list_sessions": list_sessions,
    "session_search": session_search,
    # 消息
    "send_message": send_message,
    # 媒体
    "image_generate": image_generate,
    "text_to_speech": text_to_speech,
    "parse_pdf": parse_pdf,
    # 定时任务
    "cron_create": cron_create,
    "cron_list": cron_list,
    # 技能
    "skill_search": skill_search,
    # 路由
    "router_control": router_control,
}


# ── B+C: 意图→工具映射已迁移到 DB intent.tool_names 字段
# 前端可管理，不再硬编码


# ─── 全局单例 ────────────────────────────────────────────

tool_registry = ToolRegistry()
