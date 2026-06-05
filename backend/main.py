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
        await _init_agent()
    except Exception as e:
        logger.warning(f"Agent 引擎初始化失败（降级为纯 LLM 模式）: {e}")

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

    yield

    # 清理资源
    from app.services.ollama_service import close_ollama_client
    await close_ollama_client()
    await close_db()
    await close_redis()
    logger.info("Beautiful-Elf 后端已停止")


async def _init_agent():
    """初始化 Agent 引擎（通过 agent_service 封装）"""
    from app.core.database import AsyncSessionLocal
    from app.services.llm_provider_service import LLMProviderService
    from app.services.agent_service import agent_service

    async with AsyncSessionLocal() as db:
        provider_service = LLMProviderService()
        default_provider = await provider_service.get_default(db)

        if not default_provider:
            logger.warning("无默认 LLM 供应商，Agent 引擎跳过初始化")
            return

        success = await agent_service.initialize(
            db, provider_id=default_provider.id
        )
        if success:
            logger.info(f"Agent 引擎就绪 (provider={default_provider.name})")
        else:
            logger.warning("Agent 引擎初始化失败，降级为纯 LLM 模式")


async def _init_rag():
    """初始化 RAG 管道（知识库向量检索）"""
    from app.core.config import get_settings
    from app.services.knowledge_service import knowledge_service

    settings = get_settings()
    qdrant_url = f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"

    try:
        from app.agent.rag_pipeline import RAGPipeline

        # 获取 Embedding 模型（从 agent 模块复用）
        try:
            from llama_index.embeddings.ollama import OllamaEmbedding
            embedding = OllamaEmbedding(
                model_name="dengcao/Qwen3-Embedding-0.6B:Q8_0",
                base_url=settings.OLLAMA_HOST,
            )
        except ImportError:
            logger.warning("缺少 llama-index-embeddings-ollama，RAG 管道跳过初始化")
            return

        pipeline = RAGPipeline(
            qdrant_url=qdrant_url,
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

        # 获取 Embedding 函数
        try:
            from llama_index.embeddings.ollama import OllamaEmbedding
            embedding_model = OllamaEmbedding(
                model_name="dengcao/Qwen3-Embedding-0.6B:Q8_0",
                base_url=settings.OLLAMA_HOST,
            )
            async def embedding_func(text: str):
                return await embedding_model.aget_text_embedding(text)
        except ImportError:
            logger.warning("缺少 llama-index-embeddings-ollama，记忆管理器跳过初始化")
            return

        qdrant_mapper = QdrantMapper()
        manager = MemoryManager(
            qdrant_mapper=qdrant_mapper,
            embedding_func=embedding_func,
        )

        memory_service.set_memory_manager(manager)
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

        try:
            from llama_index.embeddings.ollama import OllamaEmbedding
            embedding_model = OllamaEmbedding(
                model_name="dengcao/Qwen3-Embedding-0.6B:Q8_0",
                base_url=settings.OLLAMA_HOST,
            )
            async def embedding_func(text: str):
                return await embedding_model.aget_text_embedding(text)
        except ImportError:
            logger.warning("缺少 llama-index-embeddings-ollama，意图路由跳过初始化")
            return

        qdrant_mapper = QdrantMapper()
        router = IntentRouter(
            qdrant_mapper=qdrant_mapper,
            embedding_func=embedding_func,
        )

        intent_service.set_intent_router(router)
        logger.info("意图路由就绪")

    except Exception as e:
        logger.warning(f"意图路由初始化失败: {e}")


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
