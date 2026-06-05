"""对话上下文窗口管理 — 滑动窗口 + 摘要压缩

当对话消息超过阈值时，将旧消息压缩为摘要，保留最近消息。
防止超出 LLM 的 context window。
"""
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_CONTEXT_MESSAGES = 20


class ContextManager:
    """上下文窗口管理器"""

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LlamaIndex LLM 实例（用于摘要压缩，可选）
        """
        self.llm = llm_client

    async def trim_messages(self, messages: list, system_prompt: str = "") -> list:
        """
        超过阈值时压缩旧消息为摘要。

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示（插入到最前面）

        Returns:
            裁剪后的消息列表
        """
        if len(messages) <= MAX_CONTEXT_MESSAGES:
            result = []
            if system_prompt:
                result.append({"role": "system", "content": system_prompt})
            result.extend(messages)
            return result

        old_messages = messages[:-MAX_CONTEXT_MESSAGES]
        recent_messages = messages[-MAX_CONTEXT_MESSAGES:]

        summary = await self._summarize(old_messages)

        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        result.append({"role": "system", "content": f"【历史对话摘要】\n{summary}"})
        result.extend(recent_messages)
        return result

    async def _summarize(self, messages: list) -> str:
        """将旧消息压缩为摘要"""
        conversation = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}"
            for m in messages
        )

        prompt = f"将以下对话压缩为200字摘要，保留关键信息和用户意图：\n\n{conversation}"

        if self.llm:
            try:
                import asyncio
                result = await asyncio.to_thread(self.llm.complete, prompt)
                return str(result).strip()
            except Exception as e:
                logger.warning(f"LLM 摘要生成失败，降级为截取: {e}")

        # 降级：截取最近几条消息而非完全丢弃
        recent = messages[-5:]
        fallback = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')[:200]}"
            for m in recent
        )
        return f"（共 {len(messages)} 条历史消息，以下为最近摘要）\n{fallback}"
