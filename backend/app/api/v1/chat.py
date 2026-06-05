"""AI 对话 API — 意图路由 + Agent + 消息持久化

架构（按 architecture-upgrade.md 5.2 节）：
  用户消息 → 意图路由（快速，向量相似度，不走 LLM）
    ├─ 语义缓存命中 → 直接返回缓存答案
    ├─ 技能命中 → 路由到对应技能
    └─ 未命中 → 纯 LLM 对话（不绑工具，快）
         └─ LLM 想用工具 → 才走 Agent 引擎（绑工具）
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


# ── 意图路由 ─────────────────────────────────────────────

async def _try_intent_route(user_message: str) -> dict | None:
    """意图路由（快速路径，不走 LLM）"""
    if not intent_service.intent_router:
        return None
    try:
        result = await intent_service.intent_router.route(user_message)
        if not result:
            return None
        # 语义缓存命中
        if hasattr(result, "target_type") and result.target_type == "cache":
            return {"type": "cache", "answer": result.target_config.get("answer", ""), "score": result.score}
        # 技能命中
        if hasattr(result, "target_type") and result.target_type == "skill":
            return {"type": "skill", "intent_name": result.intent_name, "config": result.target_config}
        # 其他意图命中
        if hasattr(result, "intent_name"):
            return {"type": "intent", "intent_name": result.intent_name, "config": result.target_config}
        return None
    except Exception as e:
        logger.debug(f"意图路由失败（降级走 LLM）: {e}")
        return None


# ── 主入口 ───────────────────────────────────────────────

@router.post("/conversations/{conversation_id}/chat", response_model=ApiResult[ChatResponse])
async def chat(
    request: Request,
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequest = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ChatResponse]:
    """
    对话入口 — 意图路由 → 纯 LLM → Agent（按需）

    1. 意图路由（快速，向量相似度）
       - 语义缓存命中 → 直接返回
       - 技能命中 → 路由到技能
    2. 纯 LLM 对话（不绑工具，快速响应）
    3. 如果 LLM 想用工具 → 走 Agent 引擎（绑工具）
    """
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("CONVERSATION_VALIDATION", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]
    model_name = data.model_name or ""
    user_message = messages[-1]["content"] if messages else ""

    # ── Step 1: 意图路由（快速路径）──────────────────────
    intent = await _try_intent_route(user_message)

    if intent and intent["type"] == "cache":
        # 语义缓存命中，直接返回
        logger.info(f"[chat] 语义缓存命中 score={intent.get('score', 0):.2f}")
        return ApiResult(data=ChatResponse(
            content=intent["answer"],
            model="cache",
            provider_type="cache",
            token_count=0,
        ))

    if intent and intent["type"] == "skill":
        # 技能命中，路由到技能处理（TODO: 实现技能处理链）
        logger.info(f"[chat] 技能命中: {intent['intent_name']}")
        # 暂时降级到普通对话

    # ── Step 2: 纯 LLM 对话（不绑工具，快速）────────────
    if data.stream:
        return StreamingResponse(
            _stream_with_intent(conversation_id, messages, provider_id, model_name, intent),
            media_type="text/event-stream",
        )
    return await _chat_with_intent(conversation_id, messages, provider_id, model_name, intent, db)


# ── 非流式对话 ──────────────────────────────────────────

async def _chat_with_intent(
    conversation_id: int, messages: list, provider_id: int,
    model_name: str, intent: dict | None, db: AsyncSession,
) -> ApiResult:
    """非流式对话：纯 LLM 优先，工具调用时走 Agent"""

    # 保存用户消息
    user_content = messages[-1]["content"] if messages else ""
    try:
        await _msg_service.create_message(db, MessageCreate(
            conversation_id=conversation_id, role="user", content=user_content,
        ))
    except Exception as e:
        logger.warning(f"保存用户消息失败: {e}")

    # 纯 LLM 对话（不绑工具）
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


# ── 流式对话 ────────────────────────────────────────────

async def _stream_with_intent(
    conversation_id: int, messages: list,
    provider_id: int, model_name: str, intent: dict | None,
):
    """流式对话：纯 LLM 优先，工具调用时走 Agent"""
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

    # 纯 LLM 流式对话（不绑工具）
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
