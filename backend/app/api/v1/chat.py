"""AI 对话 API — v3.0 完整版

新增:
  1. /chat/resume 端点（interrupt/resume 审批确认）
  2. /chat/tool-stats 端点（工具使用统计）
  3. user_id 正确获取
"""
import json
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
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


class ResumeRequest(BaseModel):
    """审批恢复请求"""
    approved: bool
    tool_name: str = ""
    tool_args: Optional[dict] = None
    user_response: str = ""


class ChatRequestExtended(ChatRequest):
    """扩展聊天请求 — 新增 reasoning_depth"""
    reasoning_depth: Optional[str] = "balanced"


@router.post("/conversations/{conversation_id}/chat", response_model=ApiResult[ChatResponse])
async def chat(
    request: Request,
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequestExtended = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ChatResponse]:
    """对话入口（v4.1 — 新增 reasoning_depth + 审批/进度/引用事件）"""
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("CONVERSATION_VALIDATION", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]
    model_name = data.model_name or ""
    user_id = getattr(data, "user_id", 0) or 0
    reasoning_depth = getattr(data, "reasoning_depth", "balanced") or "balanced"

    if data.stream:
        return StreamingResponse(
            _stream_response(conversation_id, user_id, messages, provider_id, model_name, reasoning_depth),
            media_type="text/event-stream",
        )

    try:
        agent_result = await agent_service.chat(
            conversation_id=conversation_id,
            user_id=user_id,
            messages=messages,
            provider_id=provider_id,
            model_name=model_name,
        )

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


@router.post("/conversations/{conversation_id}/chat/resume", response_model=ApiResult[ChatResponse])
async def chat_resume(
    conversation_id: int = Path(..., description="会话 ID"),
    data: ResumeRequest = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ChatResponse]:
    """
    审批恢复端点（interrupt/resume）：

    当 Agent 遇到高风险工具时会暂停等待用户确认。
    前端通过此端点传入用户决定（approved/rejected）。
    """
    try:
        result = await agent_service.resume(
            conversation_id=conversation_id,
            approved=data.approved,
            tool_name=data.tool_name,
            tool_args=data.tool_args,
            user_response=data.user_response,
        )

        if "error" in result:
            return api_error("AGENT_RESUME_ERROR", result["error"], "请重试或联系管理员")

        return ApiResult(data=ChatResponse(
            content=result.get("content", ""),
            model="agent-resume",
            provider_type="agent",
            token_count=0,
        ))

    except Exception as e:
        logger.error(f"Agent resume 失败: {e}", exc_info=True)
        return api_error("AGENT_RESUME_ERROR", str(e), "请重试")


@router.get("/chat/tool-stats")
async def tool_stats() -> ApiResult[dict]:
    """工具使用统计"""
    stats = agent_service.get_tool_stats()
    return ApiResult(data=stats)


async def _stream_response(
    conversation_id: int, user_id: int, messages: list,
    provider_id: int, model_name: str, reasoning_depth: str = "balanced",
):
    # [FIX] 收集完整 AI 回复，流结束后保存到 DB
    _full_content = []

    try:
        async for event in agent_service.chat_stream(
            conversation_id=conversation_id,
            user_id=user_id,
            messages=messages,
            provider_id=provider_id,
            model_name=model_name,
            reasoning_depth=reasoning_depth,
        ):
            event_type = event.get("type", "")
            if event_type == "token":
                _full_content.append(event.get("content", ""))
                yield f"data: {json.dumps({'content': event['content'], 'done': False})}\n\n"
            elif event_type == "tool_start":
                yield f"data: {json.dumps({'tool_start': event['tool'], 'tool_args': event.get('args', {}), 'done': False})}\n\n"
            elif event_type == "tool_end":
                yield f"data: {json.dumps({'tool_end': event['tool'], 'output_preview': event.get('output_preview', ''), 'done': False})}\n\n"
            elif event_type == "intent_hit":
                yield f"data: {json.dumps({'intent_hit': event['intent'], 'intent_score': event.get('score', 0), 'done': False})}\n\n"
            elif event_type == "cost_update":
                yield f"data: {json.dumps({'cost': {'prompt_tokens': event['prompt_tokens'], 'completion_tokens': event['completion_tokens']}, 'done': False})}\n\n"
            elif event_type == "approval_required":
                # [P0] 审批事件 — 前端弹出确认对话框
                yield f"data: {json.dumps({'approval_required': {'tool': event.get('tool', ''), 'args': event.get('args', {}), 'message': event.get('message', '')}, 'done': False})}\n\n"
            elif event_type == "done":
                yield f"data: {json.dumps({'content': '', 'done': True, 'tools_used': event.get('tools_used', []), 'duration_ms': event.get('duration_ms', 0), 'prompt_tokens': event.get('prompt_tokens', 0), 'completion_tokens': event.get('completion_tokens', 0)})}\n\n"
            elif event_type == "error":
                yield f"data: {json.dumps({'error': event['message'], 'done': True})}\n\n"
    except Exception as e:
        logger.error(f"流式对话失败: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    finally:
        # [FIX] 流结束后，独立事务保存消息（不影响已发送的 SSE 流）
        assistant_content = "".join(_full_content)
        if assistant_content:
            try:
                from app.core.database import AsyncSessionLocal
                user_content = messages[-1]["content"] if messages else ""
                async with AsyncSessionLocal() as save_db:
                    await _chat_service.save_skill_messages(
                        save_db,
                        conversation_id=conversation_id,
                        user_content=user_content,
                        assistant_content=assistant_content,
                    )
                    await save_db.commit()
            except Exception as e:
                logger.warning(f"流式消息保存失败: {e}")
