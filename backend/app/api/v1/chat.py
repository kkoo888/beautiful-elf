"""AI 对话 API — POST /conversations/{id}/chat (action 模式)"""

import json
from fastapi import APIRouter, Depends, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, ConfigDict
from typing import List

from app.core.database import get_db, AsyncSessionLocal
from app.services.llm_chat_service import LLMChatService
from app.services.message_service import MessageService
from app.schemas.message import MessageCreate
from app.schemas.response import ok, fail

router = APIRouter()
_chat_service = LLMChatService()
_msg_service = MessageService()


class ChatMessage(BaseModel):
    """对话消息"""
    model_config = ConfigDict(populate_by_name=True)

    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """对话请求"""
    model_config = ConfigDict(populate_by_name=True)

    provider_id: int = Field(..., description="供应商 ID", alias="providerId")
    model_name: str = Field(..., description="模型名称", alias="modelName")
    messages: List[ChatMessage] = Field(..., description="对话历史")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    max_tokens: int = Field(default=2048, ge=1, le=32768, description="最大 token", alias="maxTokens")
    stream: bool = Field(default=True, description="是否流式返回")


@router.post("/conversations/{conversation_id}/chat")
async def chat(
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    """AI 对话 — stream=true 返回 SSE，stream=false 返回 JSON"""
    messages = [{"role": m.role, "content": m.content} for m in data.messages]

    if data.stream:
        return StreamingResponse(
            _stream_generator(conversation_id, data, messages),
            media_type="text/event-stream",
        )

    # 非流式
    try:
        result = await _chat_service.chat(
            db,
            provider_id=data.provider_id,
            model_name=data.model_name,
            messages=messages,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
        )
        # 保存 AI 回复
        try:
            await _msg_service.create(db, MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=result["content"],
                token_count=result.get("token_count", 0),
            ))
        except Exception:
            pass
        return ok(result)
    except Exception as e:
        return fail("AI_TIMEOUT", str(e), "请检查模型配置或稍后重试")


async def _stream_generator(conversation_id: int, data: ChatRequest, messages: list):
    """SSE 流式生成器"""
    full_content = ""
    try:
        async with AsyncSessionLocal() as db:
            async for chunk in _chat_service.chat_stream(
                db,
                provider_id=data.provider_id,
                model_name=data.model_name,
                messages=messages,
                temperature=data.temperature,
                max_tokens=data.max_tokens,
            ):
                full_content += chunk
                yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"

            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"

            # 流结束后保存 AI 回复
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
