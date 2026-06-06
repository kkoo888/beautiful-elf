"""AI 对话 API — 参数校验 + 调用 AgentService（v2 重构）

重构点:
  1. 所有消息统一走 Agent 图（包含意图路由 → Context → LLM → 工具）
  2. 不再有两套独立系统（旧: IntentRouter 外部 + ChatService 纯 LLM）
  3. 流式/非流式统一入口

架构（符合 Beautiful-Elf 分层规范）：
  API 层 → 只做参数校验 + 调用 service + 返回响应
  Service 层 → AgentService 编排 Agent 引擎
"""
import json
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
    对话入口（v2）：

    所有消息统一走 Agent 图：
    1. 意图路由（快速匹配技能/缓存）
    2. Context Engine 动态组装
    3. LLM 对话 + Tool Calling
    4. 记忆保存
    """
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("CONVERSATION_VALIDATION", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]
    model_name = data.model_name or ""

    # ── 流式响应 ───────────────────────────────────────
    if data.stream:
        return StreamingResponse(
            _stream_response(conversation_id, messages, provider_id, model_name),
            media_type="text/event-stream",
        )

    # ── 非流式：统一走 Agent 图 ───────────────────────
    try:
        # Agent 图已包含意图路由 + Context 组装 + LLM + 工具执行
        agent_result = await agent_service.chat(
            conversation_id=conversation_id,
            user_id=request.state.user_id if hasattr(request.state, "user_id") else 0,
            messages=messages,
            provider_id=provider_id,
            model_name=model_name,
        )

        # 保存消息到 DB
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
        logger.error(f"Agent 对话失败，降级走纯 LLM: {e}", exc_info=True)

        # 降级：纯 LLM 对话（不走 Agent 图）
        try:
            result = await _chat_service.chat(
                db, conversation_id=conversation_id, messages=messages,
                provider_id=provider_id, model_name=model_name,
            )
            return ApiResult(data=result)
        except Exception as e2:
            logger.error(f"降级 LLM 也失败: {e2}", exc_info=True)
            return api_error("AI_TIMEOUT", str(e2), "请检查模型配置或稍后重试")


async def _stream_response(
    conversation_id: int, messages: list,
    provider_id: int, model_name: str,
):
    """SSE 流式响应封装"""
    try:
        async for event in agent_service.chat_stream(
            conversation_id=conversation_id,
            user_id=0,
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
