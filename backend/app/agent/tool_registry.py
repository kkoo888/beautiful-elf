"""
工具注册表 — 桥接 DB 工具模型与 LangChain Tool Calling

架构:
  MySQL tool 表 → ToolRegistry（运行时加载） → LangChain Tool 列表
  Agent 调用 → ToolRegistry.execute() → 风险校验 → 参数校验 → 执行 → 统计记录

设计原则:
  - DB 是真相源，启动时从 MySQL 加载到内存
  - 运行时通过 name 快速查找（dict）
  - 每次执行自动记录统计（异步，不阻塞主流程）
  - 高风险工具需要 approved=True 才执行
"""
import asyncio
import logging
from typing import Any, Callable, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum

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
    运行时工具注册表

    内置工具通过 register() 注册 Python 函数
    DB 工具通过 load_from_db() 从 MySQL 加载
    两者统一通过 execute() 执行
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
            # 不覆盖已注册的内置工具（内置工具优先）
            if tool.name in self._tools:
                # 更新 DB 元数据到已有内置工具
                existing = self._tools[tool.name]
                existing.id = tool.id
                existing.risk_level = RiskLevel(tool.risk_level)
                continue

            self._tools[tool.name] = ToolDef(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                parameters=tool.json_schema or {},
                risk_level=RiskLevel(tool.risk_level),
                module=tool.module,
                func=None,  # DB 工具没有 Python 函数，需要外部提供执行器
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

    def get_langchain_tools(self) -> list:
        """返回 LangChain Tool 列表（用于 bind_tools）"""
        from langchain_core.tools import tool as lc_tool
        tools = []
        for t in self._tools.values():
            # DB 工具没有 func，用通用执行包装器
            func = t.func or self._make_db_tool_wrapper(t.name)
            tools.append(lc_tool(func, name=t.name, description=t.description))
        return tools

    def _make_db_tool_wrapper(self, tool_name: str) -> Callable:
        """为 DB 工具创建通用执行包装器（不自动批准，高风险工具需审批）"""
        async def db_tool_wrapper(**kwargs) -> str:
            result = await self.execute(tool_name, kwargs, approved=False)
            return str(result)
        return db_tool_wrapper

    # ─── 执行 ─────────────────────────────────────────

    async def execute(
        self,
        name: str,
        arguments: dict,
        approved: bool = False,
        db_session=None,
    ) -> Any:
        """
        执行工具

        1. 查找工具定义
        2. 风险校验（HIGH 需要 approved=True）
        3. 参数校验（jsonschema）
        4. 执行（内置函数或返回待执行信号）
        5. 记录统计（异步）

        Args:
            name: 工具名称
            arguments: 工具参数
            approved: 是否已获批准（高风险工具需要）
            db_session: 数据库会话（用于记录统计，可选）

        Returns:
            执行结果 dict
        """
        import time
        t = self._tools.get(name)
        if not t:
            return {"error": f"工具 '{name}' 不存在"}

        # 风险校验
        if t.risk_level == RiskLevel.HIGH and not approved:
            return {
                "needs_approval": True,
                "tool": name,
                "arguments": arguments,
                "risk_level": t.risk_level.value,
                "message": f"⚠️ {name} 是高风险操作，需要用户确认",
            }

        # 参数校验
        try:
            import jsonschema
            jsonschema.validate(arguments, t.parameters)
        except ImportError:
            pass  # jsonschema 未安装时跳过
        except jsonschema.ValidationError as e:
            return {"error": f"参数校验失败: {e.message}"}

        # 执行
        start_time = time.time()
        success = True
        result = None

        try:
            if t.func:
                # 内置工具：直接调用 Python 函数
                if asyncio.iscoroutinefunction(t.func):
                    result = await t.func(**arguments)
                else:
                    result = t.func(**arguments)
            else:
                # DB 工具：返回工具定义，由调用方决定如何执行
                result = {
                    "tool": name,
                    "arguments": arguments,
                    "module": t.module,
                    "message": f"工具 '{name}' 已触发，由模块 '{t.module}' 处理",
                }
        except Exception as e:
            logger.error(f"工具 {name} 执行异常: {e}")
            result = {"error": str(e)}
            success = False

        duration_ms = int((time.time() - start_time) * 1000)

        # 异步记录统计（不阻塞返回）
        # 注意：db_session 必须在任务执行时仍有效，否则统计会静默失败
        if db_session and t.id > 0:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._record_stats(db_session, t.id, success, duration_ms))
            except RuntimeError:
                logger.debug("无法创建统计任务：无运行中的事件循环")

        return result

    async def _record_stats(self, db_session, tool_id: int, success: bool, duration_ms: int):
        """异步记录工具调用统计"""
        try:
            from app.repository.tool_repo import ToolRepository
            repo = ToolRepository()
            await repo.record_call(db_session, tool_id, success, duration_ms)
        except Exception as e:
            logger.warning(f"工具统计记录失败: {e}")


# ─── 内置工具实现 ─────────────────────────────────────────

async def web_search(query: str, max_results: int = 5) -> dict:
    """搜索互联网获取实时信息"""
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
        return {"results": [
            {"title": r["title"], "url": r["href"], "snippet": r["body"]}
            for r in results
        ]}


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
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
    return {
        "stdout": stdout.decode()[:5000],
        "stderr": stderr.decode()[:2000],
        "exit_code": proc.returncode,
    }


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
    """查询数据库（只读 SELECT）"""
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return {"error": "只允许 SELECT 查询"}
    if "LIMIT" not in sql_upper:
        sql = sql.rstrip(";") + " LIMIT 100"

    from app.core.database import get_db_session
    async with get_db_session() as session:
        result = await session.execute(sql)
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"columns": columns, "rows": rows, "count": len(rows)}


# ─── 全局单例 ────────────────────────────────────────────

tool_registry = ToolRegistry()


def register_builtin_tools():
    """注册内置工具（应用启动时调用）"""
    tool_registry.register(
        "web_search", web_search,
        description="搜索互联网获取实时信息",
        parameters={"type": "object", "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5},
        }, "required": ["query"]},
        risk_level="low",
        module="builtin",
    )

    tool_registry.register(
        "execute_code", execute_code,
        description="在沙箱中执行代码",
        parameters={"type": "object", "properties": {
            "language": {"type": "string", "enum": ["python", "javascript"]},
            "code": {"type": "string"},
        }, "required": ["language", "code"]},
        risk_level="high",
        module="builtin",
    )

    tool_registry.register(
        "read_file", read_file,
        description="读取工作空间中的文件",
        parameters={"type": "object", "properties": {
            "path": {"type": "string"},
        }, "required": ["path"]},
        risk_level="low",
        module="builtin",
    )

    tool_registry.register(
        "query_database", query_database,
        description="查询数据库（只读 SELECT）",
        parameters={"type": "object", "properties": {
            "sql": {"type": "string"},
        }, "required": ["sql"]},
        risk_level="medium",
        module="builtin",
    )
