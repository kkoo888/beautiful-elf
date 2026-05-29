"""健康检查端点 — RESTful 规范"""
from fastapi import APIRouter
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.redis_client import get_redis
from app.core.qdrant_client import get_qdrant
from app.core.logging import get_logger
from app.schemas.response import ok

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def health_check():
    """存活检查"""
    return ok({"status": "alive"})


@router.get("/ready")
async def ready_check():
    """就绪检查 - 检测所有依赖"""
    checks = {}

    # MySQL
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["mysql"] = {"status": "ok"}
    except Exception as e:
        checks["mysql"] = {"status": "error", "detail": str(e)}

    # Redis
    try:
        r = get_redis()
        await r.ping()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)}

    # Qdrant
    try:
        q = get_qdrant()
        q.get_collections()
        checks["qdrant"] = {"status": "ok"}
    except Exception as e:
        checks["qdrant"] = {"status": "error", "detail": str(e)}

    all_ok = all(c["status"] == "ok" for c in checks.values())
    return ok({"status": "ready" if all_ok else "not_ready", "checks": checks})


@router.get("/deps")
async def deps_check():
    """依赖详情"""
    deps = {}

    # MySQL
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT VERSION()"))
            version = result.scalar()
        deps["mysql"] = {"version": version, "status": "ok"}
    except Exception as e:
        deps["mysql"] = {"status": "error", "detail": str(e)}

    # Redis
    try:
        r = get_redis()
        info = await r.info("server")
        deps["redis"] = {"version": info.get("redis_version", "unknown"), "status": "ok"}
    except Exception as e:
        deps["redis"] = {"status": "error", "detail": str(e)}

    # Qdrant
    try:
        q = get_qdrant()
        collections = q.get_collections().collections
        deps["qdrant"] = {
            "collections": len(collections),
            "status": "ok",
        }
    except Exception as e:
        deps["qdrant"] = {"status": "error", "detail": str(e)}

    return ok(deps)
