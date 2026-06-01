"""AI 对话 API — 统一入口，支持所有 LLM 供应商"""

import json
import uuid
from fastapi import APIRouter, Depends, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional

from app.core.database import get_db
from app.services.llm_chat_service import LLMChatService
from app.services.message_service import MessageService
from app.schemas.response import ok, fail

router = APIRouter()
_chat_service = LLMChatService()
_msg_service = MessageService()


class ChatMessage(BaseModel):
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    provider_id: int = Field(..., description="供应商 ID")
    model_name: str = Field(..., description="模型名称")
    messages: List[ChatMessage] = Field(..., description="对话历史")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    max_tokens: int = Field(default=2048, ge=1, le=32768, description="最大 token")
    stream: bool = Field(default=True, description="是否流式")


@router.post("/conversations/{conversation_id}/chat")
async def chat(
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    """AI 对话 — 非流式"""
    try:
        messages = [{"role": m.role, "content": m.content} for m in data.messages]
        result = await _chat_service.chat(
            db,
            provider_id=data.provider_id,
            model_name=data.model_name,
            messages=messages,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
        )

        # 保存 AI 回复到数据库
        try:
            await _msg_service.create(db, type("Msg", (), {
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": result["content"],
                "tool_calls": None,
                "tool_call_id": None,
                "token_count": result.get("token_count", 0),
            })())
        except Exception:
            pass  # 保存失败不影响回复

        return ok(result)
    except Exception as e:
        return fail("AI_TIMEOUT", str(e), "请检查模型配置或稍后重试")


@router.post("/conversations/{conversation_id}/chat/stream")
async def chat_stream(
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    """AI 对话 — 流式 SSE"""

    async def generate():
        full_content = ""
        try:
            messages = [{"role": m.role, "content": m.content} for m in data.messages]
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
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as save_db:
                    await _msg_service.create(save_db, type("Msg", (), {
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "content": full_content,
                        "tool_calls": None,
                        "tool_call_id": None,
                        "token_count": 0,
                    })())
                    await save_db.commit()
            except Exception:
                pass

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
