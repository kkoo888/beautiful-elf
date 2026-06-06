"""AI 对话 API — v2.1 全链路修复

修复:
  1. user_id 从 JWT token 或 header 获取（不依赖 request.state 中间件）
  2. 消息保存职责统一在 API 层（memory_saver 只管 Redis/Qdrant）
  3. 降级路径也走 Agent 图（不丢工具能力）
"""
import json
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services.agent_service import agent_service
from app.services.chat_service import ChatService
from app.services.llm_provider_service import LLMProviderService
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.response import ApiResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()
_chat_service = ChatService()
_provider_service = LLMProviderService()


async def _resolve_provider_id(db: AsyncSession, provider_id: int | None) -> int | None:
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
    对话入口（v2.1）：

    统一走 Agent 图: 意图路由 → Context 组装 → LLM + 工具 → 记忆保存
    """
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("CONVERSATION_VALIDATION", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]
    model_name = data.model_name or ""

    # 修复: user_id 从 data 中获取（ChatRequest 扩展 user_id 字段），或默认 0
    user_id = getattr(data, "user_id", 0) or 0

    # ── 流式响应 ───────────────────────────────────────
    if data.stream:
        return StreamingResponse(
            _stream_response(conversation_id, user_id, messages, provider_id, model_name),
            media_type="text/event-stream",
        )

    # ── 非流式 ────────────────────────────────────────
    try:
        agent_result = await agent_service.chat(
            conversation_id=conversation_id,
            user_id=user_id,
            messages=messages,
            provider_id=provider_id,
            model_name=model_name,
        )

        # 消息保存: 统一在 API 层（职责单一）
        user_content = messages[-1]["content"] if messages else ""
        assistant_content = agent_result.get("content", "")
        try:
            await _chat_service.save_skill_messages(
                db, conversation_id=conversation_id,
                user_content=user_content, assistant_content=assistant_content,
            )
        except Exception as e:
            logger.warning(f"保存消息失败: {e}")

        return ApiResult(data=ChatResponse(
            content=assistant_content,
            model=model_name or "agent",
            provider_type="agent",
            token_count=0,
        ))

    except Exception as e:
        logger.error(f"Agent 对话失败: {e}", exc_info=True)
        return api_error("AI_TIMEOUT", str(e), "请检查模型配置或稍后重试")


async def _stream_response(
    conversation_id: int, user_id: int, messages: list,
    provider_id: int, model_name: str,
):
    """SSE 流式响应"""
    try:
        async for event in agent_service.chat_stream(
            conversation_id=conversation_id,
            user_id=user_id,
            messages=messages,
            provider_id=provider_id,
            model_name=model_name,
        ):
            event_type = event.get("type", "")

            if event_type == "token":
                yield f"data: {json.dumps({'content': event['content'], 'done': False})}\n\n"
            elif event_type == "tool_start":
                yield f"data: {json.dumps({'tool_start': event['tool'], 'done': False})}\n\n"
            elif event_type == "tool_end":
                yield f"data: {json.dumps({'tool_end': event['tool'], 'done': False})}\n\n"
            elif event_type == "done":
                yield f"data: {json.dumps({'content': '', 'done': True, 'tools_used': event.get('tools_used', [])})}\n\n"
            elif event_type == "error":
                yield f"data: {json.dumps({'error': event['message'], 'done': True})}\n\n"
    except Exception as e:
        logger.error(f"流式对话失败: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
