"""AI 对话 API — 参数校验 + 调用 ChatService

架构（符合 Beautiful-Elf 分层规范）：
  API 层 → 只做参数校验 + 调用 service + 返回响应
  Service 层 → 业务编排（消息保存 + LLM 调用）
"""
import json
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.chat_service import ChatService
from app.services.llm_provider_service import LLMProviderService
from app.services.intent_service import intent_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.response import ApiResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()
_chat_service = ChatService()
_provider_service = LLMProviderService()


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

    # ── Step 2: 调用 ChatService ────────────────────────
    if data.stream:
        return StreamingResponse(
            _stream_response(conversation_id, messages, provider_id, model_name),
            media_type="text/event-stream",
        )

    try:
        result = await _chat_service.chat(
            db, conversation_id=conversation_id, messages=messages,
            provider_id=provider_id, model_name=model_name,
        )
        return ApiResult(data=result)
    except Exception as e:
        logger.error(f"LLM 对话失败: {e}", exc_info=True)
        return api_error("AI_TIMEOUT", str(e), "请检查模型配置或稍后重试")


async def _stream_response(
    conversation_id: int, messages: list,
    provider_id: int, model_name: str,
):
    """SSE 流式响应封装"""
    try:
        async for chunk in _chat_service.chat_stream(
            conversation_id=conversation_id, messages=messages,
            provider_id=provider_id, model_name=model_name,
        ):
            yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
        # generator 正常结束，发 done 信号
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
    except Exception as e:
        logger.error(f"LLM 流式对话失败: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
