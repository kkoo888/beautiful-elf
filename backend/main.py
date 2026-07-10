"""FastAPI 入口"""
import asyncio
import threading
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

    # Agent 引擎改为懒加载（用户首次对话时自动初始化），启动时不再预加载

    # 初始化 RAG 管道（可选，失败不影响基础功能）
    try:
        await _init_rag()
    except Exception as e:
        logger.warning(f"RAG 管道初始化失败（知识库功能不可用）: {e}")

    # 初始化记忆管理器（可选，失败不影响基础功能）
    try:
        await _init_memory()
    except Exception as e:
        logger.warning(f"记忆管理器初始化失败（记忆功能不可用）: {e}")

    # 初始化意图路由（可选，失败不影响基础功能）
    try:
        await _init_intent()
    except Exception as e:
        logger.warning(f"意图路由初始化失败（意图匹配不可用）: {e}")

    # 启动 MCP Server（后台任务，供 Agent 和外部客户端调用）
    try:
        await _start_mcp_server()
    except Exception as e:
        logger.warning(f"MCP Server 启动失败（MCP 功能不可用）: {e}")

    # 启动记忆定时任务调度器（替代 Celery Beat）
    try:
        from app.tasks.scheduler import start_scheduler
        from app.repository.memory_setting_repo import MemorySettingRepository
        _scheduler_repo = MemorySettingRepository()
        async with AsyncSessionLocal() as db:
            _scheduler_settings = await _scheduler_repo.find_all_scheduler_settings(db)
        start_scheduler(settings=[
            {
                "setting_key": s.setting_key,
                "is_enabled": s.is_enabled,
                "interval_seconds": s.interval_seconds,
            }
            for s in _scheduler_settings
        ])
    except Exception as e:
        logger.warning(f"定时任务调度器启动失败: {e}")

    # 启动性能监控自动采集（后台任务，每 30 秒采样一次）
    try:
        _start_perf_collector()
    except Exception as e:
        logger.warning(f"性能采集启动失败: {e}")

    # 初始化可观测性（可选）
    try:
        from app.agent.tracing import init_tracing
        init_tracing()
    except Exception as e:
        logger.warning(f"可观测性初始化失败: {e}")

    yield

    # 停止定时任务调度器
    try:
        from app.tasks.scheduler import stop_scheduler
        await stop_scheduler()
    except Exception:
        pass

    # 清理资源
    from app.services.ollama_service import close_ollama_client
    await close_ollama_client()

    # daemon 线程随进程退出，无需显式 cancel
    if _mcp_thread and _mcp_thread.is_alive():
        logger.info("MCP Server 线程随进程退出")

    # 取消性能采集任务
    if _perf_task:
        _perf_task.cancel()
        logger.info("性能采集已停止")

    await close_db()
    await close_redis()
    logger.info("Beautiful-Elf 后端已停止")


async def _init_rag():
    """初始化 RAG 管道（知识库向量检索）"""
    from app.services.knowledge_service import knowledge_service

    try:
        from app.agent.rag_pipeline import RAGPipeline

        # 获取 Embedding 模型（ONNX 本地推理）
        from app.services.onnx_embedding_service import get_onnx_embedding_service, OnnxLlamaIndexEmbedding
        onnx_svc = await get_onnx_embedding_service()
        embedding = OnnxLlamaIndexEmbedding(onnx_svc)

        pipeline = RAGPipeline(
            embedding_model=embedding,
        )
        await pipeline.initialize()
        knowledge_service.set_rag_pipeline(pipeline)
        logger.info("RAG 管道就绪")

    except Exception as e:
        logger.warning(f"RAG 管道初始化失败: {e}")


async def _init_memory():
    """初始化记忆管理器（Redis 会话缓存 + Qdrant 长期记忆）"""
    from app.core.config import get_settings
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.services.memory_service import memory_service

    settings = get_settings()

    try:
        from app.agent.memory_manager import MemoryManager

        # 获取 Embedding 函数（ONNX 本地推理）
        from app.services.onnx_embedding_service import get_onnx_embedding_service
        onnx_svc = await get_onnx_embedding_service()
        async def embedding_func(text: str):
            return await onnx_svc.get_embedding(text)

        # Reranker（可选，ONNX Cross-Encoder 精排）
        reranker = None
        try:
            from app.services.onnx_reranker_service import get_onnx_reranker_service
            reranker = await get_onnx_reranker_service()
        except Exception:
            pass

        qdrant_mapper = QdrantMapper()
        manager = MemoryManager(
            qdrant_mapper=qdrant_mapper,
            embedding_func=embedding_func,
            reranker=reranker,
        )

        memory_service.set_memory_manager(manager)
        from app.services.markdown_memory_service import markdown_memory_service
        markdown_memory_service.set_memory_manager(manager)
        logger.info("记忆管理器就绪")

    except Exception as e:
        logger.warning(f"记忆管理器初始化失败: {e}")


async def _init_intent():
    """初始化意图路由（向量相似度匹配）"""
    from app.core.config import get_settings
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.services.intent_service import intent_service

    settings = get_settings()

    try:
        from app.agent.intent_router import IntentRouter

        # 获取 Embedding 函数（ONNX 本地推理）
        from app.services.onnx_embedding_service import get_onnx_embedding_service
        onnx_svc = await get_onnx_embedding_service()
        async def embedding_func(text: str):
            return await onnx_svc.get_embedding(text)

        qdrant_mapper = QdrantMapper()
        router = IntentRouter(
            qdrant_mapper=qdrant_mapper,
            embedding_func=embedding_func,
        )

        intent_service.set_intent_router(router)
        logger.info("意图路由就绪")

    except Exception as e:
        logger.warning(f"意图路由初始化失败: {e}")


async def _start_mcp_server():
    """启动 MCP Server（后台进程，Streamable HTTP 传输，DB 驱动工具）

    v3.0 变更:
      - transport: "sse" → "http"（Streamable HTTP，MCP 2025-06-18 规范）
      - 来源: https://gofastmcp.com/getting-started/quickstart
    """
    import asyncio

    try:
        from app.agent.mcp_server import mcp_app, init_mcp_server
        from app.agent.tool_registry import tool_registry

        # 从 DB 加载工具到 MCP Server
        await init_mcp_server(tool_registry)

        host = settings.MCP_SERVER_HOST
        port = settings.MCP_SERVER_PORT

        # 在独立线程中运行（mcp_app.run 内部会创建自己的事件循环）
        global _mcp_thread
        _mcp_thread = threading.Thread(
            target=mcp_app.run,
            kwargs={"transport": "http", "host": host, "port": port},
            daemon=True,
            name="mcp-server",
        )
        _mcp_thread.start()
        logger.info(f"MCP Server 后台启动: {host}:{port} (Streamable HTTP, thread={_mcp_thread.ident})")

    except ImportError as e:
        logger.warning(f"fastmcp 未安装，MCP Server 跳过: {e}")
    except Exception as e:
        logger.warning(f"MCP Server 启动失败: {e}")


# MCP Server 线程引用
_mcp_thread: threading.Thread | None = None

# 性能采集后台任务（shutdown 时取消）
_perf_task: asyncio.Task | None = None


def _start_perf_collector(interval: int = 30):
    """启动性能监控自动采集（后台 asyncio 任务，每 interval 秒采样一次）"""
    from app.core.database import AsyncSessionLocal
    from app.services.performance_service import PerformanceService
    from app.repository.performance_repo import PerformanceRepo

    global _perf_task

    async def _collect_loop():
        service = PerformanceService(PerformanceRepo())
        while True:
            try:
                await asyncio.sleep(interval)
                async with AsyncSessionLocal() as db:
                    await service.collect_and_store(db)
                    await db.commit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"性能采集异常: {e}")
                await asyncio.sleep(interval)

    _perf_task = asyncio.create_task(_collect_loop())
    logger.info(f"性能采集已启动（每 {interval} 秒采样）")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# 限流
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from fastapi.responses import JSONResponse

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        resp = JSONResponse(
            status_code=429,
            content={"code": "SYSTEM_RATE_LIMIT", "message": "请求过于频繁", "user_tip": "请稍后重试"},
        )
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp
except ImportError:
    pass  # slowapi 未安装时跳过限流

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id", "Content-Range", "Accept-Ranges", "Content-Length"],
)


# 全局异常处理
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    resp = JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "userTip": exc.user_tip,
            "data": None,
            "requestId": getattr(request.state, "trace_id", ""),
        },
    )
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    resp = JSONResponse(
        status_code=500,
        content={
            "code": "SYSTEM_INTERNAL_ERROR",
            "message": "服务器内部错误",
            "userTip": "系统繁忙，请稍后重试",
            "data": None,
            "requestId": getattr(request.state, "trace_id", ""),
        },
    )
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    resp = JSONResponse(
        status_code=400,
        content={
            "code": "SYSTEM_VALIDATION",
            "message": str(exc),
            "userTip": str(exc),
            "data": None,
            "requestId": getattr(request.state, "trace_id", ""),
        },
    )
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


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

# 静态文件挂载（品牌图片等用户上传资源）
import os
from fastapi.staticfiles import StaticFiles
_uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(_uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=6680, reload=True)
