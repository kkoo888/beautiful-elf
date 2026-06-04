"""AI 对话 API — POST /conversations/{id}/chat"""
import json
from fastapi import APIRouter, Depends, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.services.llm_chat_service import LLMChatService
from app.services.llm_provider_service import LLMProviderService
from app.services.message_service import MessageService
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.message import MessageCreate
from app.schemas.response import ApiResult, api_error

router = APIRouter()
_chat_service = LLMChatService()
_provider_service = LLMProviderService()
_msg_service = MessageService()


async def _resolve_provider_id(db: AsyncSession, provider_id: int | None) -> int | None:
    """解析供应商 ID：前端未传时自动使用默认供应商"""
    if provider_id is not None:
        return provider_id
    default_provider = await _provider_service.get_default(db)
    return default_provider.id if default_provider else None


@router.post("/conversations/{conversation_id}/chat", response_model=ApiResult[ChatResponse])
async def chat(
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequest = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ChatResponse]:
    """AI 对话 — stream=true 返回 SSE，stream=false 返回 JSON"""
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("NO_PROVIDER", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]

    if data.stream:
        return StreamingResponse(
            _stream_generator(conversation_id, provider_id, data, messages),
            media_type="text/event-stream",
        )

    try:
        result = await _chat_service.chat(
            db,
            provider_id=provider_id,
            model_name=data.model_name,
            messages=messages,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
        )
        try:
            await _msg_service.create(db, MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=result.content,
                token_count=result.token_count,
            ))
        except Exception:
            pass
        return ApiResult(data=result)
    except Exception as e:
        return api_error("AI_TIMEOUT", str(e), "请检查模型配置或稍后重试")


async def _stream_generator(
    conversation_id: int, provider_id: int, data: ChatRequest, messages: list,
):
    """SSE 流式生成器"""
    full_content = ""
    try:
        async with AsyncSessionLocal() as db:
            async for chunk in _chat_service.chat_stream(
                db,
                provider_id=provider_id,
                model_name=data.model_name,
                messages=messages,
                temperature=data.temperature,
                max_tokens=data.max_tokens,
            ):
                full_content += chunk
                yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"

            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"

            try:
                await _msg_service.create(db, MessageCreate(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
                    token_count=0,
                ))
                await db.commit()
            except Exception:
                pass
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
