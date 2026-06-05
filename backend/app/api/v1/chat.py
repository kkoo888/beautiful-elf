"""AI 对话 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
业务逻辑全部在 agent_service / llm_chat_service 中
"""
import json
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.services.llm_chat_service import LLMChatService
from app.services.llm_provider_service import LLMProviderService
from app.services.message_service import MessageService
from app.services.agent_service import agent_service
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
    default_provider = await _provider_service.get_default(db)
    return default_provider.id if default_provider else None


@router.post("/conversations/{conversation_id}/chat", response_model=ApiResult[ChatResponse])
async def chat(
    request: Request,
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequest = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ChatResponse]:
    """Agent 对话 — 自动选择 Agent 模式或纯 LLM 模式"""
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("CONVERSATION_NO_PROVIDER", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]

    # Agent 模式
    if agent_service.is_ready:
        if data.stream:
            return StreamingResponse(
                _agent_stream(conversation_id, messages),
                media_type="text/event-stream",
            )
        return await _agent_chat(conversation_id, messages, db)

    # 降级：纯 LLM 模式
    if data.stream:
        return StreamingResponse(
            _llm_stream(conversation_id, provider_id, data, messages, db),
            media_type="text/event-stream",
        )
    return await _llm_chat(conversation_id, provider_id, data, messages, db)


# ── Agent 对话 ────────────────────────────────────────────

async def _agent_chat(conversation_id: int, messages: list, db: AsyncSession) -> ApiResult:
    """Agent 非流式对话"""
    try:
        result = await agent_service.chat(
            conversation_id=conversation_id,
            user_id=0,
            messages=messages,
        )

        # 保存消息
        try:
            await _msg_service.create(db, MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=result["content"],
            ))
        except Exception as e:
            logger.warning(f"保存消息失败（非致命）: {e}")

        return ApiResult(data=ChatResponse(
            content=result["content"],
            model="agent",
            provider_type="agent",
            token_count=0,
        ))

    except Exception as e:
        logger.error(f"Agent 对话失败: {e}", exc_info=True)
        return api_error("AI_INTERNAL_ERROR", str(e), "AI 对话失败，请稍后重试")


async def _agent_stream(conversation_id: int, messages: list):
    """Agent SSE 流式输出"""
    full_content = ""
    tools_used = []

    try:
        async for event in agent_service.chat_stream(
            conversation_id=conversation_id,
            user_id=0,
            messages=messages,
        ):
            event_type = event.get("type", "")

            if event_type == "token":
                token = event["content"]
                full_content += token
                yield f"data: {json.dumps({'content': token, 'done': False})}\n\n"

            elif event_type == "tool_start":
                tools_used.append(event["tool"])
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['tool']})}\n\n"

            elif event_type == "tool_end":
                yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['tool']})}\n\n"

            elif event_type == "done":
                tools_used = event.get("tools_used", tools_used)
                yield f"data: {json.dumps({'content': '', 'done': True, 'tools_used': tools_used})}\n\n"

            elif event_type == "error":
                yield f"data: {json.dumps({'error': event['message'], 'done': True})}\n\n"

        # 保存消息
        if full_content:
            try:
                async with AsyncSessionLocal() as save_db:
                    await _msg_service.create(save_db, MessageCreate(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=full_content,
                    ))
                    await save_db.commit()
            except Exception as e:
                logger.warning(f"Agent 流式保存消息失败: {e}")

    except Exception as e:
        logger.error(f"Agent 流式对话失败: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"


# ── 纯 LLM 对话（降级）────────────────────────────────────

async def _llm_chat(
    conversation_id: int, provider_id: int, data: ChatRequest, messages: list, db: AsyncSession
) -> ApiResult:
    """纯 LLM 非流式对话"""
    try:
        result = await _llm_chat_service.chat(
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
        except Exception as e:
            logger.warning(f"保存消息失败（非致命）: {e}")
        return ApiResult(data=result)
    except Exception as e:
        return api_error("AI_TIMEOUT", str(e), "请检查模型配置或稍后重试")


async def _llm_stream(
    conversation_id: int, provider_id: int, data: ChatRequest, messages: list, db: AsyncSession
):
    """纯 LLM SSE 流式输出"""
    full_content = ""
    try:
        async with AsyncSessionLocal() as stream_db:
            async for chunk in _llm_chat_service.chat_stream(
                stream_db,
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
                await _msg_service.create(stream_db, MessageCreate(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
                    token_count=0,
                ))
                await stream_db.commit()
            except Exception as e:
                logger.warning(f"保存流式消息失败（非致命）: {e}")
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
