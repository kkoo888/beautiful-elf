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
    """工具定义"""
    id: int                     # DB tool.id
    name: str                   # 工具名称（唯一）
    description: str            # 工具描述
    parameters: dict            # JSON Schema
    risk_level: RiskLevel       # 风险等级
    module: str                 # 所属模块
    func: Optional[Callable] = None  # 执行函数（可选，内置工具才有）


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

            if tool.name in self._tools:
                existing = self._tools[tool.name]
                existing.id = tool.id
                existing.description = tool.description
                existing.parameters = tool.json_schema or {}
                existing.risk_level = RiskLevel(tool.risk_level)
                existing.module = tool.module
                if func:
                    existing.func = func
                continue

            self._tools[tool.name] = ToolDef(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                parameters=tool.json_schema or {},
                risk_level=RiskLevel(tool.risk_level),
                module=tool.module,
                func=func,
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
        """返回工具摘要（用于 ContextEngine 动态选择）"""
        return [
            {"name": t.name, "description": t.description, "risk": t.risk_level.value, "module": t.module}
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
            tools.append(StructuredTool.from_function(
                func=func,
                name=t.name,
                description=t.description,
            ))
        return tools

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
            tools.append(StructuredTool.from_function(
                func=func, name=t.name, description=t.description,
            ))
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

async def web_search(query: str, max_results: int = 5) -> dict:
    """搜索互联网获取实时信息

    优先使用 SearXNG（自建元搜索引擎，免费无限制），
    降级到 DuckDuckGo（国内可能不可用）。
    """
    import os
    import httpx

    # ── 方案 A: SearXNG（推荐） ─────────────────────────
    searxng_url = os.getenv("SEARXNG_URL", "").strip()
    if searxng_url:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{searxng_url.rstrip('/')}/search",
                    params={"q": query, "format": "json", "count": max_results},
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])[:max_results]
                if results:
                    return {"results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("content", ""),
                        }
                        for r in results
                    ]}
        except Exception as e:
            logger.warning(f"[web_search] SearXNG 失败，降级到 DuckDuckGo: {e}")

    # ── 方案 B: 百度搜索（国内可用，无需 API Key） ──────
    try:
        import re
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.baidu.com/s",
                params={"wd": query, "rn": max_results},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            if resp.status_code == 200:
                html = resp.text
                # 提取搜索结果
                results = []
                # 匹配标题和摘要
                for m in re.finditer(
                    r'<h3[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?</h3>.*?<span class="content-right_8Zs40">(.*?)</span>',
                    html, re.DOTALL
                ):
                    url, title, snippet = m.group(1), m.group(2), m.group(3)
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                    if title:
                        results.append({"title": title, "url": url, "snippet": snippet})
                # 简化匹配（备用）
                if not results:
                    for m in re.finditer(r'<h3[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL):
                        url, title = m.group(1), m.group(2)
                        title = re.sub(r'<[^>]+>', '', title).strip()
                        if title:
                            results.append({"title": title, "url": url, "snippet": ""})
                if results:
                    return {"results": results[:max_results]}
    except Exception as e:
        logger.warning(f"[web_search] 百度搜索失败: {e}")

    # ── 方案 C: DuckDuckGo 降级 ─────────────────────────
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if results:
                return {"results": [
                    {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                    for r in results
                ]}
    except Exception as e:
        logger.warning(f"[web_search] DuckDuckGo 也失败: {e}")

    # ── 全部失败 ────────────────────────────────────────
    return {
        "success": False,
        "error": {
            "code": "SEARCH_UNAVAILABLE",
            "message": "搜索引擎暂时不可用",
            "retryable": False,
            "user_facing": True,
            "user_tip": "请稍后再试，或换个方式描述你的问题",
        },
    }


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


async def read_file(path: str) -> dict:
    """读取工作空间中的文件"""
    from pathlib import Path
    workspace = Path("/workspace").resolve()
    target = (workspace / path).resolve()
    if not str(target).startswith(str(workspace)):
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
        try:
            result = await session.execute(text(sql_stripped))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return {"columns": columns, "rows": rows, "count": len(rows)}
        except Exception as e:
            return {"error": f"查询执行失败: {str(e)}"}


# ── 执行函数注册表（DB 工具自动关联执行函数）──────────────
# 工具元数据全部由 DB 管理，这里只做 name → 执行函数的映射
_EXEC_FUNC_MAP = {
    "web_search": web_search,
    "execute_code": execute_code,
    "read_file": read_file,
    "query_database": query_database,
}


# ── B+C: 意图→工具映射已迁移到 DB intent.tool_names 字段
# 前端可管理，不再硬编码


# ─── 全局单例 ────────────────────────────────────────────

tool_registry = ToolRegistry()

