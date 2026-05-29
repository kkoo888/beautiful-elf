"""FastAPI 入口"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.exceptions import AppError
from app.core.logging import setup_logging, get_logger, trace_id_var
from app.api.v1 import health, config, schedule, clipboard, snippet
from app.api.v1 import (
    conversation,
    message,
    pet,
    notification,
    performance,
    command,
    soul_config,
)

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
    yield

    # 清理资源
    await engine.dispose()
    logger.info("Beautiful-Elf 后端已停止")


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
            "request_id": getattr(request.state, "trace_id", ""),
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
            "request_id": getattr(request.state, "trace_id", ""),
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
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(config.router, prefix="/api/v1", tags=["config"])
app.include_router(schedule.router, prefix="/api/v1/schedules", tags=["schedule"])
app.include_router(clipboard.router, prefix="/api/v1/clipboard-items", tags=["clipboard"])
app.include_router(snippet.router, prefix="/api/v1/snippets", tags=["snippet"])
app.include_router(conversation.router, prefix="/api/v1/conversations", tags=["conversation"])
app.include_router(message.router, prefix="/api/v1/messages", tags=["message"])
app.include_router(pet.router, prefix="/api/v1/pet-attributes", tags=["pet"])
app.include_router(notification.router, prefix="/api/v1/notifications", tags=["notification"])
app.include_router(performance.router, prefix="/api/v1/performance", tags=["performance"])
app.include_router(command.router, prefix="/api/v1/commands", tags=["command"])
app.include_router(soul_config.router, prefix="/api/v1/soul-configs", tags=["soul_config"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
