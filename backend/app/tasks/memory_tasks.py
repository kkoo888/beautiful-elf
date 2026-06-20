"""记忆定时任务 — 纯 async 实现（由 scheduler.py 调度）

任务:
  - check_idle_summaries: 每 5 分钟，30 分钟无互动的会话存压缩摘要 + 自动创建经历
  - memory_decay_sweep: 每 6 小时，ACT-R 衰减扫描，标记 dormant
  - observation_freshness_sweep: 每周，observation 新鲜度自动衰减
  - process_summary_queue: 每分钟，消费摘要队列（异步化写入）
  - sleeptime_consolidation: 每日凌晨，Sleep-Time Compute 深度记忆整理

防重策略:
  - check_idle_summaries: Redis 分布式锁(5min TTL) + watermark(只处理 last_active > 上次扫描时间)
  - sleeptime_consolidation: Redis 分布式锁(24h TTL)
  - memory_decay_sweep / observation_freshness_sweep: 天然幂等，无需加锁
  - process_summary_queue: Redis LPOP 原子操作，天然安全
"""
from datetime import datetime, timedelta
import json

from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_idle_summaries():
    """每 5 分钟：30 分钟无互动 → 存压缩摘要 + 创建经历"""
    from app.core.redis_client import get_redis
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.core.database import AsyncSessionLocal
    from app.repository.conversation_repo import ConversationRepository
    from app.core.task_lock import distributed_lock, get_watermark, set_watermark

    redis = get_redis()

    async with distributed_lock(redis, "check_idle_summaries", ttl_seconds=280) as acquired:
        if not acquired:
            return

        watermark_str = await get_watermark(redis, "check_idle_summaries")
        watermark_dt = datetime.fromisoformat(watermark_str) if watermark_str else None

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

        reranker = None
        try:
            from app.services.onnx_reranker_service import get_onnx_reranker_service
            reranker = await get_onnx_reranker_service()
        except Exception:
            pass

        memory = MemoryManager(
            qdrant_mapper=qdrant_mapper,
            embedding_func=embedding_func,
            llm_client=llama_llm,
            reranker=reranker,
        )

        now = datetime.utcnow()
        cursor = 0
        processed = 0
        episode_created = 0
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

                if now - last_dt < timedelta(minutes=30):
                    continue

                if watermark_dt and last_dt <= watermark_dt:
                    continue

                conv_id = int(key.split(":")[-1])

                try:
                    async with AsyncSessionLocal() as db:
                        conv_repo = ConversationRepository()
                        conv = await conv_repo.find_by_id(db, conv_id)
                        if conv:
                            summary_result = await memory.save_summary(
                                conversation_id=conv_id,
                                user_id=conv.user_id,
                                messages=cache.get("messages", []),
                            )
                            processed += 1

                            if summary_result:
                                try:
                                    from app.services.markdown_memory_service import markdown_memory_service
                                    ep = await markdown_memory_service.create_episode_from_conversation(
                                        db, conv_id, conv.user_id, cache.get("messages", []),
                                    )
                                    if ep:
                                        episode_created += 1
                                except Exception as ep_err:
                                    logger.warning(f"经历创建失败(非致命): conv={conv_id} err={ep_err}")

                    await redis.delete(key)
                except Exception as e:
                    logger.warning(f"check_idle_summaries: 会话 {conv_id} 失败: {e}")

            if cursor == 0:
                break

        await set_watermark(redis, "check_idle_summaries", now.isoformat())
        if processed:
            logger.info(f"check_idle_summaries: 归档 {processed} 个空闲会话, 创建 {episode_created} 个经历")


async def memory_decay_sweep():
    """每 6 小时：ACT-R 衰减扫描，标记 dormant + 归档 + 物理删除"""
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.services.memory_decay_service import MemoryDecayService

    qdrant_mapper = QdrantMapper()
    decay_service = MemoryDecayService()

    marked = decay_service.batch_mark_dormant(qdrant_mapper)
    if marked:
        logger.info(f"memory_decay_sweep: 标记 {marked} 条记忆为 dormant")

    backfilled = decay_service.backfill_existing(qdrant_mapper)
    if backfilled:
        logger.info(f"memory_decay_sweep: 回填 {backfilled} 条存量 payload")

    archived = decay_service.archive_old_dormant(qdrant_mapper, base_days=90)
    if archived:
        logger.info(f"memory_decay_sweep: 归档 {archived} 条过期 dormant 记忆")

    deleted = decay_service.cleanup_archived(qdrant_mapper)
    if deleted:
        logger.info(f"memory_decay_sweep: 物理删除 {deleted} 条 archived 记忆")


async def process_summary_queue():
    """每分钟：消费摘要队列，LLM 结构化 + embedding + Qdrant 存储"""
    from app.core.redis_client import get_redis
    from app.mappers.qdrant_mapper import QdrantMapper

    redis = get_redis()
    qdrant_mapper = QdrantMapper()

    try:
        from app.services.onnx_embedding_service import get_onnx_embedding_service
        onnx_svc = await get_onnx_embedding_service()
        async def embedding_func(text: str):
            return await onnx_svc.get_embedding(text)
    except Exception:
        return

    try:
        from llama_index.llms.ollama import Ollama as OllamaLLM
        from app.core.config import get_settings
        settings = get_settings()
        llama_llm = OllamaLLM(model="qwen3.5:7b", base_url=settings.OLLAMA_HOST)
    except ImportError:
        llama_llm = None

    from app.agent.memory_manager import MemoryManager

    reranker = None
    try:
        from app.services.onnx_reranker_service import get_onnx_reranker_service
        reranker = await get_onnx_reranker_service()
    except Exception:
        pass

    memory = MemoryManager(
        qdrant_mapper=qdrant_mapper,
        embedding_func=embedding_func,
        llm_client=llama_llm,
        reranker=reranker,
    )

    processed = 0
    batch_size = 50
    for _ in range(batch_size):
        raw = await redis.lpop("memory:summary_queue")
        if not raw:
            break

        try:
            data = json.loads(raw)
            meta = await memory._process_summary(data)

            if meta and meta.get("point_id"):
                try:
                    from app.core.database import AsyncSessionLocal
                    from app.repository.memory_repo import MemoryRepository
                    async with AsyncSessionLocal() as db:
                        repo = MemoryRepository()
                        messages = data.get("messages", [])
                        content_text = "\n".join(
                            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                            for m in messages[-10:]
                        )
                        await repo.create(db, {
                            "conversation_id": data["conversation_id"],
                            "content": content_text[:2000],
                            "summary": meta["summary"],
                            "tags": meta["tags"],
                            "importance": meta["importance"],
                            "qdrant_point_id": meta["point_id"],
                        })
                        await db.commit()
                except Exception as mysql_err:
                    logger.warning(f"process_summary_queue: MySQL 同步失败(非致命): {mysql_err}")

            processed += 1
        except Exception as e:
            logger.warning(f"process_summary_queue: 处理失败: {e}")
            try:
                retry_data = json.loads(raw)
                retry_count = retry_data.get("_retry_count", 0) + 1
                if retry_count <= 3:
                    retry_data["_retry_count"] = retry_count
                    await redis.rpush(
                        "memory:summary_queue",
                        json.dumps(retry_data, ensure_ascii=False),
                    )
            except Exception:
                pass

    if processed:
        logger.info(f"process_summary_queue: 处理 {processed} 条摘要")


async def observation_freshness_sweep():
    """每周：observation 新鲜度自动衰减"""
    from app.core.database import AsyncSessionLocal
    from app.services.markdown_memory_service import markdown_memory_service

    async with AsyncSessionLocal() as db:
        stats = await markdown_memory_service.sweep_freshness(db)
        await db.commit()

    logger.info(
        f"observation_freshness_sweep: "
        f"new→stable={stats['new_to_stable']}, "
        f"stable→weakening={stats['stable_to_weakening']}, "
        f"weakening→stale={stats['weakening_to_stale']}"
    )


async def sleeptime_consolidation():
    """每日凌晨：Sleep-Time Compute 深度记忆整理"""
    from app.core.task_lock import distributed_lock

    redis_conn = None
    try:
        from app.core.redis_client import get_redis
        redis_conn = get_redis()
    except Exception:
        pass

    if redis_conn:
        async with distributed_lock(redis_conn, "sleeptime_consolidation", ttl_seconds=86400) as acquired:
            if not acquired:
                return
            await _run_sleeptime_consolidation()
    else:
        await _run_sleeptime_consolidation()


async def _run_sleeptime_consolidation():
    """实际执行 Sleep-Time Compute（已持锁）"""
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.agent.sleeptime_agent import SleepTimeAgent
    from app.core.database import AsyncSessionLocal

    qdrant_mapper = QdrantMapper()

    try:
        from app.services.onnx_embedding_service import get_onnx_embedding_service
        onnx_svc = await get_onnx_embedding_service()
        async def embedding_func(text: str):
            return await onnx_svc.get_embedding(text)
    except Exception:
        logger.warning("sleeptime_consolidation: 缺少 embedding 依赖，跳过")
        return

    llama_llm = None
    try:
        from llama_index.llms.ollama import Ollama as OllamaLLM
        from app.core.config import get_settings
        import os
        settings = get_settings()
        model_name = os.environ.get("SLEEPTIME_MODEL", "qwen3.5:7b")
        llama_llm = OllamaLLM(model=model_name, base_url=settings.OLLAMA_HOST)
    except ImportError:
        pass

    user_ids = []
    try:
        from sqlalchemy import select, distinct
        from app.models.observation import MemoryObservation
        async with AsyncSessionLocal() as db:
            stmt = select(distinct(MemoryObservation.user_id)).where(
                MemoryObservation.is_deleted == 0
            )
            result = await db.execute(stmt)
            user_ids = [row[0] for row in result.all()]
    except Exception as e:
        logger.warning(f"sleeptime_consolidation: 获取用户列表失败: {e}")
        user_ids = [0]

    if not user_ids:
        return

    total_result = {"phase_a": {"merged": 0, "deleted": 0, "kept": 0},
                    "phase_b": {"entities_created": 0, "relations_created": 0},
                    "phase_c": {"insights_created": 0}}

    for uid in user_ids:
        agent = SleepTimeAgent(
            qdrant_mapper=qdrant_mapper,
            embedding_func=embedding_func,
            llm_client=llama_llm,
            max_items=200,
        )
        try:
            result = await agent.run(user_id=uid)
            for phase in ("phase_a", "phase_b", "phase_c"):
                for k, v in result.get(phase, {}).items():
                    total_result[phase][k] = total_result[phase].get(k, 0) + v
        except Exception as e:
            logger.warning(f"sleeptime_consolidation: 用户 {uid} 处理失败: {e}")

    logger.info(
        f"sleeptime_consolidation 完成 ({len(user_ids)} 用户): "
        f"Phase A(合并)={total_result['phase_a']}, "
        f"Phase B(实体)={total_result['phase_b']}, "
        f"Phase C(洞察)={total_result['phase_c']}"
    )
