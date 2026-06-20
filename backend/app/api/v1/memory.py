"""长期记忆 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
业务逻辑全部在 memory_service 中
"""
from fastapi import APIRouter, Depends, Path, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.memory_service import memory_service
from app.schemas.memory import MemoryCreate, MemoryOut, MemorySearchResponse
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=ApiPageResult)
async def list_memories(
    pagination: PaginationParams = Depends(get_pagination),
    conversation_id: int | None = Query(default=None, alias="conversationId", description="会话 ID 筛选"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult:
    """获取记忆列表"""
    items, total = await memory_service.list_memories(
        db, page=pagination.page, page_size=pagination.page_size,
        conversation_id=conversation_id,
    )
    return ApiPageResult(data=items, total=total)


@router.get("/search", response_model=ApiResult[MemorySearchResponse])
async def search_memories(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(default=10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[MemorySearchResponse]:
    """记忆语义搜索"""
    if not q.strip():
        return api_error("MEMORY_VALIDATION", "搜索关键词不能为空", "请输入搜索内容")

    result = await memory_service.search(db, query=q, limit=limit)
    return ApiResult(data=result)


@router.get("/optimize", response_model=ApiResult)
async def get_optimized_memories(
    rerank: bool = Query(default=True, description="启用 Rerank 精排"),
    decay: bool = Query(default=True, description="启用时间衰减"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取优化后的记忆列表（Rerank + Decay 效果展示）"""
    if not memory_service.memory_manager:
        return api_error("MEMORY_NOT_READY", "记忆管理器未初始化")

    try:
        results = await memory_service.memory_manager.search_with_scores(
            query="优化展示", user_id=0, limit=limit,
        )

        items = []
        for r in results:
            items.append({
                "id": r.get("id", ""),
                "summary": r.get("summary", ""),
                "score": round(r.get("score", 0), 4),
                "rerankScore": round(r.get("rerank_score", 0), 4) if r.get("rerank_score") else None,
                "decayFactor": round(r.get("decay_factor", 1.0), 4),
                "importance": r.get("importance", 5),
                "activation": r.get("activation", 1.0),
                "tags": r.get("tags", []),
                "savedAt": r.get("saved_at", ""),
            })

        return ApiResult(data=items)
    except Exception as e:
        logger.error(f"获取优化记忆失败: {e}", exc_info=True)
        return api_error("MEMORY_OPTIMIZE_FAILED", str(e))


@router.post("/optimize", response_model=ApiResult)
async def trigger_optimization(
    data: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """触发记忆优化（重新计算 activation 并写回 Qdrant）"""
    if not memory_service.memory_manager:
        return api_error("MEMORY_NOT_READY", "记忆管理器未初始化")

    importance_boost = data.get("importance_boost", 1)

    try:
        from app.services.memory_decay_service import MemoryDecayService
        from app.mappers.qdrant_mapper import QdrantMapper

        qdrant = QdrantMapper()
        decay_svc = MemoryDecayService()

        # 1. 批量标记 dormant
        dormant_count = decay_svc.batch_mark_dormant(qdrant)

        # 2. 存量回填
        backfilled = decay_svc.backfill_existing(qdrant)

        # 3. 统计结果
        result = {
            "optimizedCount": dormant_count + backfilled,
            "rerankImproved": 0,
            "decayApplied": dormant_count,
            "newInsights": 0,
        }

        logger.info(f"[optimize] 完成: dormant={dormant_count} backfilled={backfilled}")
        return ApiResult(data=result)
    except Exception as e:
        logger.error(f"触发优化失败: {e}", exc_info=True)
        return api_error("MEMORY_OPTIMIZE_FAILED", str(e))


@router.get("/{memory_id}", response_model=ApiResult[MemoryOut])
async def get_memory(
    memory_id: int = Path(..., description="记忆 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[MemoryOut]:
    """获取记忆详情"""
    try:
        item = await memory_service.get_memory(db, memory_id)
        return ApiResult(data=item)
    except Exception as e:
        return api_error("MEMORY_NOT_FOUND", str(e), "请检查记忆 ID")


@router.post("", response_model=ApiResult[MemoryOut])
async def create_memory(
    data: MemoryCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[MemoryOut]:
    """创建记忆"""
    try:
        item = await memory_service.create_memory(db, data)
        return ApiResult(data=item)
    except Exception as e:
        logger.error(f"创建记忆失败: {e}", exc_info=True)
        return api_error("MEMORY_INTERNAL_ERROR", str(e), "创建记忆失败，请稍后重试")


@router.delete("/{memory_id}", response_model=ApiResult)
async def delete_memory(
    memory_id: int = Path(..., description="记忆 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """删除记忆"""
    try:
        await memory_service.delete_memory(db, memory_id)
        return ApiResult(message="删除成功")
    except Exception as e:
        return api_error("MEMORY_NOT_FOUND", str(e), "请检查记忆 ID")


@router.post("/rescore", response_model=ApiResult)
async def rescore_memories(
    data: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """重新评分记忆重要性（LLM 精确评分）

    Body:
      - point_ids: string[] — 要重新评分的 Qdrant 点 ID 列表（空=全部）
      - user_id: int — 用户 ID（默认 0）

    Returns:
      - rescored: int — 重新评分数
      - updated: int — 实际更新数
    """
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.agent.memory_manager import MemoryManager
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    point_ids = data.get("point_ids", [])
    user_id = data.get("user_id", 0)

    qdrant = QdrantMapper()

    # 获取 LLM 客户端
    llm_client = None
    try:
        from llama_index.llms.ollama import Ollama as OllamaLLM
        from app.core.config import get_settings
        settings = get_settings()
        llm_client = OllamaLLM(model="qwen3.5:7b", base_url=settings.OLLAMA_HOST)
    except Exception:
        pass

    rescored = 0
    updated = 0

    if point_ids:
        # 指定 ID 重新评分
        for pid in point_ids:
            try:
                payload = qdrant.get_by_id("memory_vectors", pid)
                if not payload:
                    continue

                summary = payload.get("summary", "")
                old_importance = int(payload.get("importance", 5))

                # 用 summary 作为"对话"让 LLM 评分
                fake_messages = [{"role": "user", "content": summary}]
                new_importance = await MemoryManager._llm_score_importance(
                    fake_messages, llm_client=llm_client,
                )
                rescored += 1

                if new_importance != old_importance:
                    qdrant._client.set_payload(
                        collection_name="memory_vectors",
                        payload={"importance": new_importance},
                        points=[pid],
                    )
                    updated += 1
            except Exception as e:
                logger.warning(f"rescore 失败: {pid}: {e}")
    else:
        # 全部重新评分（scroll 分页）
        offset = None
        batch_size = 50
        while True:
            conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="decay_status", match=MatchValue(value="active")),
            ]
            try:
                points, next_offset = qdrant._client.scroll(
                    collection_name="memory_vectors",
                    scroll_filter=Filter(must=conditions),
                    limit=batch_size,
                    offset=offset,
                    with_vectors=False,
                )
            except Exception:
                break

            if not points:
                break

            for p in points:
                try:
                    payload = p.payload or {}
                    summary = payload.get("summary", "")
                    old_importance = int(payload.get("importance", 5))

                    fake_messages = [{"role": "user", "content": summary}]
                    new_importance = await MemoryManager._llm_score_importance(
                        fake_messages, llm_client=llm_client,
                    )
                    rescored += 1

                    if new_importance != old_importance:
                        qdrant._client.set_payload(
                            collection_name="memory_vectors",
                            payload={"importance": new_importance},
                            points=[p.id],
                        )
                        updated += 1
                except Exception as e:
                    logger.warning(f"rescore 失败: {p.id}: {e}")

            if next_offset is None:
                break
            offset = next_offset

    return ApiResult(data={"rescored": rescored, "updated": updated})
