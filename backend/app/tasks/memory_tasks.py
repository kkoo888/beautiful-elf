"""Celery 定时任务 — 记忆归档

任务:
  - hourly_detail_save: 每小时，活跃会话存详细日志到 Qdrant
  - check_idle_summaries: 每 5 分钟，30 分钟无互动的会话存压缩摘要

注意:
  - Celery 任务使用 asyncio.run() 创建独立事件循环
  - 仅在 prefork 模式下安全
  - 如果 worker 使用 gevent/eventlet，需替换为 gevent.monkey.patch_all()
"""
from celery import shared_task
from datetime import datetime, timedelta
import asyncio
import json

from app.core.logging import get_logger

logger = get_logger(__name__)


@shared_task
def hourly_detail_save():
    """每小时：活跃会话存详细日志"""
    asyncio.run(_hourly_detail_save())


async def _hourly_detail_save():
    """异步实现：扫描 Redis 活跃会话，存详细日志到 Qdrant"""
    from app.core.redis_client import get_redis
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.core.database import AsyncSessionLocal
    from app.repository.conversation_repo import ConversationRepository

    redis = get_redis()
    qdrant_mapper = QdrantMapper()

    try:
        from app.services.onnx_embedding_service import get_onnx_embedding_service
        onnx_svc = await get_onnx_embedding_service()
        async def embedding_func(text: str):
            return await onnx_svc.get_embedding(text)
    except Exception:
        logger.warning("hourly_detail_save: 缺少 embedding 依赖，跳过")
        return

    from app.agent.memory_manager import MemoryManager
    memory = MemoryManager(
        qdrant_mapper=qdrant_mapper,
        embedding_func=embedding_func,
    )

    cursor = 0
    processed = 0
    while True:
        cursor, keys = await redis.scan(cursor, match="memory:session:*", count=100)
        for key in keys:
            data = await redis.get(key)
            if not data:
                continue

            cache = json.loads(data)
            last_active = cache.get("last_active")
            if not last_active:
                continue

            last_dt = datetime.fromisoformat(last_active)
            if datetime.utcnow() - last_dt > timedelta(hours=1):
                continue

            conv_id = int(key.split(":")[-1])

            try:
                async with AsyncSessionLocal() as db:
                    conv_repo = ConversationRepository()
                    conv = await conv_repo.find_by_id(db, conv_id)
                    if conv:
                        await memory.save_detail(
                            conversation_id=conv_id,
                            user_id=conv.user_id,
                            messages=cache.get("messages", []),
                        )
                        processed += 1
            except Exception as e:
                logger.warning(f"hourly_detail_save: 会话 {conv_id} 失败: {e}")

        if cursor == 0:
            break

    logger.info(f"hourly_detail_save: 处理 {processed} 个活跃会话")


@shared_task
def check_idle_summaries():
    """每 5 分钟：30 分钟无互动 → 存压缩摘要"""
    asyncio.run(_check_idle_summaries())


async def _check_idle_summaries():
    """异步实现：扫描 Redis 空闲会话，存压缩摘要到 Qdrant"""
    from app.core.redis_client import get_redis
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.core.database import AsyncSessionLocal
    from app.repository.conversation_repo import ConversationRepository

    redis = get_redis()
    qdrant_mapper = QdrantMapper()

    try:
        from app.services.onnx_embedding_service import get_onnx_embedding_service
        onnx_svc = await get_onnx_embedding_service()
        async def embedding_func(text: str):
            return await onnx_svc.get_embedding(text)
    except Exception:
        logger.warning("check_idle_summaries: 缺少 embedding 依赖，跳过")
        return

    try:
        from llama_index.llms.ollama import Ollama as OllamaLLM
        from app.core.config import get_settings
        settings = get_settings()
        llama_llm = OllamaLLM(model="qwen3.5:7b", base_url=settings.OLLAMA_HOST)
    except ImportError:
        llama_llm = None

    from app.agent.memory_manager import MemoryManager
    memory = MemoryManager(
        qdrant_mapper=qdrant_mapper,
        embedding_func=embedding_func,
        llm_client=llama_llm,
    )

    cursor = 0
    processed = 0
    while True:
        cursor, keys = await redis.scan(cursor, match="memory:session:*", count=100)
        for key in keys:
            data = await redis.get(key)
            if not data:
                continue

            cache = json.loads(data)
            last_active = cache.get("last_active")
            if not last_active:
                continue

            last_dt = datetime.fromisoformat(last_active)
            if datetime.utcnow() - last_dt < timedelta(minutes=30):
                continue

            conv_id = int(key.split(":")[-1])

            try:
                async with AsyncSessionLocal() as db:
                    conv_repo = ConversationRepository()
                    conv = await conv_repo.find_by_id(db, conv_id)
                    if conv:
                        await memory.save_summary(
                            conversation_id=conv_id,
                            user_id=conv.user_id,
                            messages=cache.get("messages", []),
                        )
                        processed += 1

                # 删除 Redis 缓存（已归档）
                await redis.delete(key)
            except Exception as e:
                logger.warning(f"check_idle_summaries: 会话 {conv_id} 失败: {e}")

        if cursor == 0:
            break

    logger.info(f"check_idle_summaries: 归档 {processed} 个空闲会话")
