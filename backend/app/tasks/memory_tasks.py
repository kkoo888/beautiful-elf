"""Celery 定时任务 — 记忆归档 + 衰减 + 经历 + 新鲜度衰减 + 异步写入

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
def check_idle_summaries():
    """每 5 分钟：30 分钟无互动 → 存压缩摘要"""
    asyncio.run(_check_idle_summaries())


async def _check_idle_summaries():
    """异步实现：扫描 Redis 空闲会话，存压缩摘要到 Qdrant

    防重策略:
      - distributed_lock: 5min TTL，防并发执行
      - watermark: 记录上次扫描完成时间，只处理 last_active > watermark 的会话
    """
    from app.core.redis_client import get_redis
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.core.database import AsyncSessionLocal
    from app.repository.conversation_repo import ConversationRepository
    from app.core.task_lock import distributed_lock, get_watermark, set_watermark

    redis = get_redis()

    # 加锁 + watermark 检查（双重防重）
    async with distributed_lock(redis, "check_idle_summaries", ttl_seconds=280) as acquired:
        if not acquired:
            return

        # 获取上次扫描水位线
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

                # 跳过: 不够 30 分钟空闲
                if now - last_dt < timedelta(minutes=30):
                    continue

                # watermark 防重: 跳过上次扫描已处理过的会话
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

        # 更新水位线为本次扫描开始时间
        await set_watermark(redis, "check_idle_summaries", now.isoformat())
        logger.info(f"check_idle_summaries: 归档 {processed} 个空闲会话, 创建 {episode_created} 个经历")


# ═══════════════════════════════════════════════════
# v5.0 Task 2: 认知衰减 Sweep
# ═══════════════════════════════════════════════════

@shared_task
def memory_decay_sweep():
    """每 6 小时：ACT-R 衰减扫描，批量标记 dormant"""
    asyncio.run(_memory_decay_sweep())


async def _memory_decay_sweep():
    """异步实现：扫描 Qdrant 记忆，按 ACT-R 激活度标记 dormant + 清理过期记忆"""
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.services.memory_decay_service import MemoryDecayService

    qdrant_mapper = QdrantMapper()
    decay_service = MemoryDecayService()

    # 1. 批量标记 dormant（仅标记，不逐条计算）
    marked = decay_service.batch_mark_dormant(qdrant_mapper)
    logger.info(f"memory_decay_sweep: 标记 {marked} 条记忆为 dormant")

    # 2. 存量回填（幂等操作，只在首次有效）
    backfilled = decay_service.backfill_existing(qdrant_mapper)
    if backfilled:
        logger.info(f"memory_decay_sweep: 回填 {backfilled} 条存量 payload")

    # 3. dormant 分级归档（importance 1-4:90天, 5-7:180天, 8-10:永不归档）
    archived = decay_service.archive_old_dormant(qdrant_mapper, base_days=90)
    if archived:
        logger.info(f"memory_decay_sweep: 归档 {archived} 条过期 dormant 记忆")

    # 4. 物理删除所有 archived 记忆
    deleted = cleanup_archived_memories(qdrant_mapper)
    if deleted:
        logger.info(f"memory_decay_sweep: 物理删除 {deleted} 条 archived 记忆")


async def cleanup_archived_memories(qdrant_mapper) -> int:
    """物理删除所有 archived 记忆"""
    from app.services.memory_decay_service import MemoryDecayService
    return MemoryDecayService().cleanup_archived(qdrant_mapper)


# ═══════════════════════════════════════════════════
# v5.1 Task: 摘要写入异步化
# ═══════════════════════════════════════════════════

@shared_task
def process_summary_queue():
    """每分钟: 消费摘要队列，异步执行 LLM + embedding + Qdrant 存储

    流程:
      1. 从 Redis list memory:summary_queue 批量取出任务
      2. 对每条执行 _process_summary (LLM 结构化 + embedding + Qdrant upsert)
      3. 同步写入 MySQL memory_entry 表
    """
    asyncio.run(_process_summary_queue())


async def _process_summary_queue():
    """异步实现: 摘要队列消费"""
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
        logger.warning("process_summary_queue: 缺少 embedding 依赖，跳过")
        return

    try:
        from llama_index.llms.ollama import Ollama as OllamaLLM
        from app.core.config import get_settings
        settings = get_settings()
        llama_llm = OllamaLLM(model="qwen3.5:7b", base_url=settings.OLLAMA_HOST)
    except ImportError:
        llama_llm = None

    from app.agent.memory_manager import MemoryManager

    # v5.0: 注入 reranker（可选）
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

    # 每次最多处理 50 条（避免单次任务耗时过长）
    processed = 0
    batch_size = 50
    for _ in range(batch_size):
        raw = await redis.lpop("memory:summary_queue")
        if not raw:
            break

        try:
            data = json.loads(raw)
            meta = await memory._process_summary(data)

            # 同步写入 MySQL memory_entry 表
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
            # v5.1 fix: 失败消息重试入队（最多 3 次）
            try:
                retry_data = json.loads(raw)
                retry_count = retry_data.get("_retry_count", 0) + 1
                if retry_count <= 3:
                    retry_data["_retry_count"] = retry_count
                    await redis.rpush(
                        "memory:summary_queue",
                        json.dumps(retry_data, ensure_ascii=False),
                    )
                    logger.info(f"process_summary_queue: 消息已重试 ({retry_count}/3)")
                else:
                    logger.warning(f"process_summary_queue: 消息重试次数耗尽，丢弃")
            except Exception:
                pass  # 重试入队失败，记录日志

    if processed:
        logger.info(f"process_summary_queue: 处理 {processed} 条摘要")


# ═══════════════════════════════════════════════════════
# v5.1 Task: Observation 新鲜度衰减
# ═══════════════════════════════════════════════════════

@shared_task
def observation_freshness_sweep():
    """每周: observation 新鲜度自动衰减

    衰减规则:
      - new >14天 → stable
      - stable >60天无更新 → weakening
      - weakening >30天 → stale
    """
    asyncio.run(_observation_freshness_sweep())


async def _observation_freshness_sweep():
    """异步实现: observation 新鲜度扫描"""
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


# ═══════════════════════════════════════════════════════
# v5.1 Task 2.1: Sleep-Time Compute Agent
# ═══════════════════════════════════════════════════════

@shared_task
def sleeptime_consolidation():
    """每日凌晨: Sleep-Time Compute 深度记忆整理

    三阶段管线:
      Phase A: 碎片合并（近 7 天 detail/summary LLM 合并去重）
      Phase B: 知识图谱更新（新 summary 实体+关系抽取）
      Phase C: 洞察触发（高重要性记忆触发 reflect）

    防重策略: distributed_lock 24h TTL，同一时间只执行一次
    """
    asyncio.run(_sleeptime_consolidation())


async def _sleeptime_consolidation():
    """异步实现: Sleep-Time Compute

    v5.1 fix: 按用户分批执行，避免跨用户记忆混合。
    防重: Redis 分布式锁 24h TTL
    """
    from app.core.task_lock import distributed_lock

    redis_conn = None
    try:
        from app.core.redis_client import get_redis
        redis_conn = get_redis()
    except Exception:
        pass

    # 加锁防重入（24h TTL）
    if redis_conn:
        async with distributed_lock(redis_conn, "sleeptime_consolidation", ttl_seconds=86400) as acquired:
            if not acquired:
                return
            await _run_sleeptime_consolidation()
    else:
        # 无 Redis 时降级为直接执行（单实例场景安全）
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

    # 尝试使用更强的模型（可配置 SLEEPTIME_MODEL）
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

    # 获取所有活跃用户 ID
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
        # 降级为默认用户
        user_ids = [0]

    if not user_ids:
        logger.info("sleeptime_consolidation: 无活跃用户，跳过")
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
            # 累加统计
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
