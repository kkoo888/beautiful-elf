"""Auto-Compaction — 自动压缩对话历史

设计动机（借鉴 OpenClaw）:
  - 当对话接近 context window 上限时，自动压缩旧历史
  - 压缩前先保存重要记忆（pre-flush）
  - 用 LLM 将旧消息摘要为结构化总结
  - 保留最近 N 条消息不压缩

流程:
  1. 检测 token 使用量是否接近上限
  2. 触发 pre-flush（保存重要记忆到长期存储）
  3. 将旧消息用 LLM 压缩为摘要
  4. 用摘要替代旧消息，保留最近消息
"""
from typing import List, Dict, Any, Optional
import json

from app.core.logging import get_logger

logger = get_logger(__name__)

# 默认配置
DEFAULT_MAX_TOKENS = 128000       # context window 大小
DEFAULT_RESERVE_TOKENS = 20000    # 预留给生成的 token
DEFAULT_KEEP_RECENT = 10          # 保留最近 N 条消息不压缩
DEFAULT_SOFT_THRESHOLD = 4000     # 软阈值（触发 pre-flush）


class AutoCompactor:
    """自动压缩器"""

    def __init__(
        self,
        llm_client=None,
        memory_manager=None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        reserve_tokens: int = DEFAULT_RESERVE_TOKENS,
        keep_recent: int = DEFAULT_KEEP_RECENT,
        soft_threshold: int = DEFAULT_SOFT_THRESHOLD,
    ):
        self.llm = llm_client
        self.memory_manager = memory_manager
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.keep_recent = keep_recent
        self.soft_threshold = soft_threshold

    def estimate_tokens(self, messages: List[dict]) -> int:
        """粗略估算消息的 token 数（中文约 1.5 字/token，英文约 4 字符/token）"""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        # 简单估算：平均每 2 个字符 ≈ 1 token
        return total_chars // 2

    def should_compact(self, messages: List[dict]) -> bool:
        """是否需要压缩（短对话直接跳过）"""
        if len(messages) <= self.keep_recent + 5:
            return False
        estimated = self.estimate_tokens(messages)
        threshold = self.max_tokens - self.reserve_tokens
        return estimated > threshold

    def should_flush_memory(self, messages: List[dict]) -> bool:
        """是否需要 pre-flush 记忆（接近压缩阈值）"""
        estimated = self.estimate_tokens(messages)
        threshold = self.max_tokens - self.reserve_tokens - self.soft_threshold
        return estimated > threshold

    async def compact(
        self,
        messages: List[dict],
        user_id: int = 0,
        conversation_id: int = 0,
    ) -> List[dict]:
        """压缩消息列表

        Args:
            messages: 完整消息列表
            user_id: 用户 ID
            conversation_id: 会话 ID

        Returns:
            压缩后的消息列表（摘要 + 最近消息）
        """
        if len(messages) <= self.keep_recent:
            return messages

        # 分离旧消息和新消息
        old_messages = messages[:-self.keep_recent]
        recent_messages = messages[-self.keep_recent:]

        # 生成摘要
        summary = await self._generate_summary(old_messages)

        # pre-flush: 保存重要记忆
        if self.memory_manager:
            await self._flush_important_memory(old_messages, user_id, conversation_id)

        # 用摘要替代旧消息
        summary_msg = {
            "role": "system",
            "content": f"【对话历史摘要（{len(old_messages)} 条消息已压缩）】\n{summary}",
        }

        compacted = [summary_msg] + recent_messages
        logger.info(f"[compactor] 压缩: {len(messages)} → {len(compacted)} 条消息，摘要 {len(summary)} 字")
        return compacted

    async def _generate_summary(self, messages: List[dict]) -> str:
        """用 LLM 生成对话摘要"""
        text = "\n".join(f"[{m.get('role', 'user')}] {m.get('content', '')[:500]}" for m in messages)

        if not self.llm:
            # 无 LLM 时降级为截取关键信息
            return self._fallback_summary(messages)

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            response = await self.llm.ainvoke([
                SystemMessage(content=(
                    "你是一个对话压缩专家。将以下对话压缩为结构化摘要，要求：\n"
                    "1. 保留用户的核心需求和关键决定\n"
                    "2. 保留重要的事实、数字、结论\n"
                    "3. 保留待办事项和未完成的任务\n"
                    "4. 丢弃寒暄、重复、无关紧要的内容\n"
                    "5. 输出格式：要点列表，每个要点一行"
                )),
                HumanMessage(content=text[:8000]),
            ])
            return response.content.strip()

        except Exception as e:
            logger.warning(f"[compactor] LLM 摘要失败，降级: {e}")
            return self._fallback_summary(messages)

    def _fallback_summary(self, messages: List[dict]) -> str:
        """降级摘要（无 LLM 时）"""
        # 提取用户消息和工具调用
        user_msgs = [m for m in messages if m.get("role") == "user"]
        tool_msgs = [m for m in messages if m.get("role") == "tool"]

        parts = [f"共 {len(messages)} 条消息（{len(user_msgs)} 条用户消息，{len(tool_msgs)} 次工具调用）"]

        # 取最近 3 条用户消息作为摘要
        for m in user_msgs[-3:]:
            content = m.get("content", "")[:200]
            if content:
                parts.append(f"- 用户: {content}")

        return "\n".join(parts)

    async def _flush_important_memory(
        self, messages: List[dict], user_id: int, conversation_id: int
    ) -> None:
        """pre-flush: 将重要信息保存到长期记忆"""
        if not self.memory_manager:
            return

        try:
            await self.memory_manager.save_summary(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=messages,
            )
            logger.info(f"[compactor] pre-flush: 已保存长期记忆")
        except Exception as e:
            logger.warning(f"[compactor] pre-flush 失败: {e}")


# ── 模块级便捷函数 ──────────────────────────────────────

async def maybe_compact(
    messages: List[dict],
    llm_client=None,
    memory_manager=None,
    user_id: int = 0,
    conversation_id: int = 0,
) -> List[dict]:
    """检查并执行压缩（入口函数）"""
    compactor = AutoCompactor(
        llm_client=llm_client,
        memory_manager=memory_manager,
    )

    if not compactor.should_compact(messages):
        return messages

    return await compactor.compact(messages, user_id=user_id, conversation_id=conversation_id)
