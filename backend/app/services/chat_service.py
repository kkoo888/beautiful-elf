"""消息持久化 Service — 保存对话消息

职责：保存用户消息 + 助手回复到数据库。
对话编排由 agent_service（流式 SSE）负责。
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.message_service import MessageService
from app.schemas.message import MessageCreate
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """消息持久化服务"""

    def __init__(self):
        self._msg = MessageService()

    async def save_skill_messages(
        self,
        db: AsyncSession,
        conversation_id: int,
        user_content: str,
        assistant_content: str,
        token_count: int = 0,
    ) -> None:
        """保存对话消息（支持分别保存用户/助手消息）

        当 user_content 非空时保存用户消息，当 assistant_content 非空时保存助手回复。
        两个参数可以同时传（兼容旧调用），也可以只传一个。
        """
        if user_content:
            try:
                await self._msg.create_message(db, MessageCreate(
                    conversation_id=conversation_id, role="user", content=user_content,
                    tool_call_id="",
                ))
            except Exception as e:
                logger.warning(f"保存用户消息失败: {e}")

        if assistant_content:
            try:
                await self._msg.create_message(db, MessageCreate(
                    conversation_id=conversation_id, role="assistant", content=assistant_content,
                    token_count=token_count,
                    tool_call_id="",
                ))
            except Exception as e:
                logger.warning(f"保存助手消息失败: {e}")
