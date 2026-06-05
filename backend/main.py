"""FastAPI 入口"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import Base, engine, close_db
from app.core.redis_client import close_redis
from app.core.exceptions import AppError
from app.core.logging import setup_logging, get_logger, trace_id_var
from app.api.v1.api import api_router
from app.api.v1.websocket import router as ws_router

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    setup_logging()
    logger.info("Beautiful-Elf 后端启动中...")

    # 创建数据库表（开发阶段，生产用 Alembic）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表初始化完成")

    # 加载 Ollama 配置到内存缓存
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.ollama_service import load_ollama_config
        async with AsyncSessionLocal() as db:
            await load_ollama_config(db)
    except Exception as e:
        logger.warning(f"Ollama 配置加载失败（首次启动可能无数据）: {e}")

    # 初始化 Agent 引擎（可选，失败不影响基础功能）
    try:
        await _init_agent(app)
    except Exception as e:
        logger.warning(f"Agent 引擎初始化失败（降级为纯 LLM 模式）: {e}")
        app.state.agent_graph = None

    yield

    # 清理资源
    from app.services.ollama_service import close_ollama_client
    await close_ollama_client()
    await close_db()
    await close_redis()
    logger.info("Beautiful-Elf 后端已停止")


async def _init_agent(app: FastAPI):
    """
    初始化 Agent 引擎。

    从 DB 加载默认供应商 → 创建 LangChain LLM → 构建 Agent 图 → 存入 app.state
    失败时降级为纯 LLM 模式（app.state.agent_graph = None）
    """
    from app.core.database import AsyncSessionLocal
    from app.services.llm_provider_service import LLMProviderService
    from app.agent.llm_service import llm_service
    from app.agent.tool_registry import tool_registry, register_builtin_tools

    async with AsyncSessionLocal() as db:
        provider_service = LLMProviderService()
        default_provider = await provider_service.get_default(db)

        if not default_provider:
            logger.warning("无默认 LLM 供应商，Agent 引擎跳过初始化")
            app.state.agent_graph = None
            return

        # 注册内置工具
        register_builtin_tools()

        # 获取 LangChain LLM（绑定工具）
        try:
            llm = await llm_service.get_chat_llm(
                db,
                provider_id=default_provider.id,
                bind_tools=tool_registry.get_langchain_tools(),
            )
        except ImportError as e:
            logger.warning(f"缺少 LangChain 依赖: {e}")
            app.state.agent_graph = None
            return

        # 构建 Agent 图
        from app.agent.engine import build_agent_graph
        agent_graph = build_agent_graph(llm=llm, tool_registry=tool_registry)

        app.state.agent_graph = agent_graph
        logger.info(f"Agent 引擎初始化完成 (provider={default_provider.name})")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id"],
)


# 全局异常处理
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "userTip": exc.user_tip,
            "data": None,
            "requestId": getattr(request.state, "trace_id", ""),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": "SYSTEM_INTERNAL_ERROR",
            "message": "服务器内部错误",
            "userTip": "系统繁忙，请稍后重试",
            "data": None,
            "requestId": getattr(request.state, "trace_id", ""),
        },
    )


# 请求中间件：注入 trace_id
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    tid = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    request.state.trace_id = tid
    trace_id_var.set(tid)
    response = await call_next(request)
    response.headers["X-Trace-Id"] = tid
    return response


# 注册路由
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
