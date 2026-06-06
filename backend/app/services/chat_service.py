"""AI 对话 Service — 编排消息保存 + LLM 调用

职责：
  1. 保存用户消息
  2. 调用 LLM（流式 / 非流式）
  3. 保存助手回复

API 层只做参数校验 + 调用本 service。
"""
from typing import List, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal

from app.services.llm_chat_service import LLMChatService
from app.services.message_service import MessageService
from app.schemas.chat import ChatResponse
from app.schemas.message import MessageCreate
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """对话编排服务"""

    def __init__(self):
        self._llm = LLMChatService()
        self._msg = MessageService()

    async def chat(
        self,
        db: AsyncSession,
        conversation_id: int,
        messages: List[dict],
        provider_id: int,
        model_name: str,
    ) -> ChatResponse:
        """非流式对话：保存用户消息 → LLM → 保存助手回复"""

        # 1. 保存用户消息
        user_content = messages[-1]["content"] if messages else ""
        try:
            await self._msg.create_message(db, MessageCreate(
                conversation_id=conversation_id, role="user", content=user_content,
            ))
        except Exception as e:
            logger.warning(f"保存用户消息失败: {e}")

        # 2. 调用 LLM
        llm_result = await self._llm.chat(
            db, provider_id=provider_id, model_name=model_name,
            messages=messages, temperature=0.7, max_tokens=2048,
        )

        # 3. 保存助手回复
        try:
            await self._msg.create_message(db, MessageCreate(
                conversation_id=conversation_id, role="assistant",
                content=llm_result.content, token_count=llm_result.token_count,
            ))
        except Exception as e:
            logger.warning(f"保存助手消息失败: {e}")

        return llm_result

    async def save_skill_messages(
        self,
        db: AsyncSession,
        conversation_id: int,
        user_content: str,
        assistant_content: str,
    ) -> None:
        """保存技能对话的用户消息 + 助手回复"""
        try:
            await self._msg.create_message(db, MessageCreate(
                conversation_id=conversation_id, role="user", content=user_content,
            ))
        except Exception as e:
            logger.warning(f"保存用户消息失败: {e}")

        try:
            await self._msg.create_message(db, MessageCreate(
                conversation_id=conversation_id, role="assistant", content=assistant_content,
            ))
        except Exception as e:
            logger.warning(f"保存助手消息失败: {e}")

    async def chat_stream(
        self,
        conversation_id: int,
        messages: List[dict],
        provider_id: int,
        model_name: str,
    ) -> AsyncIterator[str]:
        """流式对话：保存用户消息 → 流式 LLM → 保存助手回复

        只 yield 内容 chunk，结束标记（done: true）由 API 层统一处理。
        """

        # 1. 保存用户消息（独立事务）
        user_content = messages[-1]["content"] if messages else ""
        try:
            async with AsyncSessionLocal() as save_db:
                await self._msg.create_message(save_db, MessageCreate(
                    conversation_id=conversation_id, role="user", content=user_content,
                ))
                await save_db.commit()
        except Exception as e:
            logger.warning(f"保存用户消息失败: {e}")

        # 2. 流式 LLM
        full_content = ""
        async with AsyncSessionLocal() as stream_db:
            async for chunk in self._llm.chat_stream(
                stream_db, provider_id=provider_id, model_name=model_name,
                messages=messages, temperature=0.7, max_tokens=2048,
            ):
                full_content += chunk
                yield chunk

        # 3. 流结束后保存助手回复（独立事务，不影响已发送的 SSE 流）
        if full_content:
            try:
                async with AsyncSessionLocal() as save_db:
                    await self._msg.create_message(save_db, MessageCreate(
                        conversation_id=conversation_id, role="assistant",
                        content=full_content, token_count=0,  # 流式无法精确统计 token
                    ))
                    await save_db.commit()
            except Exception as e:
                logger.warning(f"保存助手消息失败: {e}")
