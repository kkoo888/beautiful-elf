"""AI 对话 API — 意图路由 + LLM 对话

架构（architecture-upgrade.md 5.2 节）：
  用户消息 → 意图路由（快速，向量相似度）
    ├─ 语义缓存命中 → 直接返回缓存答案
    ├─ 技能命中 → 路由到对应技能（TODO）
    └─ 未命中 → 纯 LLM 对话（不绑工具，快速）
"""
import json
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.services.llm_chat_service import LLMChatService
from app.services.llm_provider_service import LLMProviderService
from app.services.message_service import MessageService
from app.services.intent_service import intent_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.message import MessageCreate
from app.schemas.response import ApiResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()
_llm_chat_service = LLMChatService()
_provider_service = LLMProviderService()
_msg_service = MessageService()


async def _resolve_provider_id(db: AsyncSession, provider_id: int | None) -> int | None:
    """解析供应商 ID：前端未传时自动使用默认供应商"""
    if provider_id is not None:
        return provider_id
    default_provider = await _provider_service.get_default_provider(db)
    return default_provider.id if default_provider else None


@router.post("/conversations/{conversation_id}/chat", response_model=ApiResult[ChatResponse])
async def chat(
    request: Request,
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequest = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ChatResponse]:
    """
    对话入口：
    1. 意图路由（快速，不走 LLM）
    2. 纯 LLM 对话（不绑工具，快速响应）
    """
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("CONVERSATION_VALIDATION", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]
    model_name = data.model_name or ""
    user_message = messages[-1]["content"] if messages else ""

    # ── Step 1: 意图路由 ─────────────────────────────────
    intent = None
    if intent_service.intent_router:
        try:
            intent = await intent_service.intent_router.route(user_message)
        except Exception as e:
            logger.debug(f"意图路由失败（降级走 LLM）: {e}")

    # 语义缓存命中，直接返回
    if intent and intent.get("cached_answer"):
        logger.info(f"[chat] 语义缓存命中 score={intent.get('score', 0):.2f}")
        return ApiResult(data=ChatResponse(
            content=intent["cached_answer"],
            model="cache",
            provider_type="cache",
            token_count=0,
        ))

    # 技能命中（TODO: 路由到技能处理链）
    if intent and intent.get("target_module"):
        logger.info(f"[chat] 意图命中: {intent['intent_name']} → {intent['target_module']}")

    # ── Step 2: 纯 LLM 对话（不绑工具）──────────────────
    if data.stream:
        return StreamingResponse(
            _llm_stream(conversation_id, messages, provider_id, model_name),
            media_type="text/event-stream",
        )
    return await _llm_chat(conversation_id, messages, provider_id, model_name, db)


# ── 非流式 LLM 对话 ────────────────────────────────────

async def _llm_chat(
    conversation_id: int, messages: list, provider_id: int,
    model_name: str, db: AsyncSession,
) -> ApiResult:
    """纯 LLM 非流式对话（不绑工具，快速响应）"""

    # 保存用户消息
    user_content = messages[-1]["content"] if messages else ""
    try:
        await _msg_service.create_message(db, MessageCreate(
            conversation_id=conversation_id, role="user", content=user_content,
        ))
    except Exception as e:
        logger.warning(f"保存用户消息失败: {e}")

    try:
        llm_result = await _llm_chat_service.chat(
            db, provider_id=provider_id, model_name=model_name,
            messages=messages, temperature=0.7, max_tokens=2048,
        )

        # 保存助手回复
        try:
            await _msg_service.create_message(db, MessageCreate(
                conversation_id=conversation_id, role="assistant",
                content=llm_result.content, token_count=llm_result.token_count,
            ))
        except Exception as e:
            logger.warning(f"保存助手消息失败: {e}")

        return ApiResult(data=llm_result)

    except Exception as e:
        logger.error(f"LLM 对话失败: {e}", exc_info=True)
        return api_error("AI_TIMEOUT", str(e), "请检查模型配置或稍后重试")


# ── 流式 LLM 对话 ──────────────────────────────────────

async def _llm_stream(
    conversation_id: int, messages: list,
    provider_id: int, model_name: str,
):
    """纯 LLM 流式对话（不绑工具，快速响应）"""
    full_content = ""

    # 保存用户消息
    user_content = messages[-1]["content"] if messages else ""
    try:
        async with AsyncSessionLocal() as save_db:
            await _msg_service.create_message(save_db, MessageCreate(
                conversation_id=conversation_id, role="user", content=user_content,
            ))
            await save_db.commit()
    except Exception as e:
        logger.warning(f"保存用户消息失败: {e}")

    try:
        async with AsyncSessionLocal() as stream_db:
            async for chunk in _llm_chat_service.chat_stream(
                stream_db, provider_id=provider_id, model_name=model_name,
                messages=messages, temperature=0.7, max_tokens=2048,
            ):
                full_content += chunk
                yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"

            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"

            # 保存助手回复
            if full_content:
                try:
                    async with AsyncSessionLocal() as save_db:
                        await _msg_service.create_message(save_db, MessageCreate(
                            conversation_id=conversation_id, role="assistant",
                            content=full_content, token_count=0,
                        ))
                        await save_db.commit()
                except Exception as e:
                    logger.warning(f"保存助手消息失败: {e}")

    except Exception as e:
        logger.error(f"LLM 流式对话失败: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
