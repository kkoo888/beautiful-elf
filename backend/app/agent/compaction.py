"""Auto-Compaction — LangGraph trim_messages 规范化（v2.0）

v2.0 重构（Harrison Chase 视角优化）:
  - 消息裁剪: LangGraph trim_messages 替代手写 _trim_messages
  - Token 估算: trim_messages 内置 tiktoken 支持（可选）
  - 摘要生成: 保留自研 LLM 摘要（官方无等价）
  - Pre-flush: 保留自研记忆保存（官方无等价）
  - 代码量: ~150 行 → ~120 行

设计动机（借鉴 OpenClaw）:
  - 当对话接近 context window 上限时，自动压缩旧历史
  - 压缩前先保存重要记忆（pre-flush）
  - 用 LLM 将旧消息摘要为结构化总结
  - 保留最近 N 条消息不压缩
"""
from typing import List, Dict, Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


def _content_to_str(content) -> str:
    """将消息 content 统一转为字符串（兼容 list content blocks 格式）"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


# 默认配置
DEFAULT_MAX_TOKENS = 128000       # context window 大小
DEFAULT_RESERVE_TOKENS = 20000    # 预留给生成的 token
DEFAULT_KEEP_RECENT = 10          # 保留最近 N 条消息不压缩
DEFAULT_SOFT_THRESHOLD = 4000     # 软阈值（触发 pre-flush）


class AutoCompactor:
    """自动压缩器（v2.0 — LangGraph trim_messages 规范化）"""

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
        """估算 token 数（v2.0: 尝试用 tiktoken，降级为字符估算）"""
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4")
            total = 0
            for m in messages:
                content = _content_to_str(m.get("content", ""))
                total += len(enc.encode(content))
            return total
        except ImportError:
            # 降级: 字符估算（中文约 1.5 字/token，英文约 4 字符/token）
            total_chars = sum(len(_content_to_str(m.get("content", ""))) for m in messages)
            return total_chars // 2

    def should_compact(self, messages: List[dict]) -> bool:
        """是否需要压缩"""
        if len(messages) <= self.keep_recent + 5:
            return False
        estimated = self.estimate_tokens(messages)
        threshold = self.max_tokens - self.reserve_tokens
        return estimated > threshold

    def should_flush_memory(self, messages: List[dict]) -> bool:
        """是否需要 pre-flush 记忆"""
        estimated = self.estimate_tokens(messages)
        threshold = self.max_tokens - self.reserve_tokens - self.soft_threshold
        return estimated > threshold

    async def compact(
        self,
        messages: List[dict],
        user_id: int = 0,
        conversation_id: int = 0,
    ) -> List[dict]:
        """压缩消息列表（v2.0: 使用 LangGraph trim_messages）

        流程:
          1. LangGraph trim_messages 裁剪到保留窗口
          2. 被裁剪的消息用 LLM 生成摘要
          3. Pre-flush 保存重要记忆
          4. 摘要 + 保留消息 = 压缩结果
        """
        if len(messages) <= self.keep_recent:
            return messages

        # ── 1. 使用 LangGraph trim_messages ──────────
        trimmed_messages, removed_messages = self._trim_with_langgraph(messages)

        # ── 2. 对被裁剪的消息生成摘要 ────────────────
        if removed_messages:
            summary = await self._generate_summary(removed_messages)

            # pre-flush: 保存重要记忆
            if self.memory_manager:
                await self._flush_important_memory(removed_messages, user_id, conversation_id)

            # 用摘要替代被裁剪的消息
            summary_msg = {
                "role": "system",
                "content": f"【对话历史摘要（{len(removed_messages)} 条消息已压缩）】\n{summary}",
            }
            result = [summary_msg] + trimmed_messages
        else:
            result = trimmed_messages

        logger.info(f"[compactor] 压缩: {len(messages)} → {len(result)} 条消息")
        return result

    def _trim_with_langgraph(self, messages: List[dict]) -> tuple:
        """使用 LangGraph trim_messages 裁剪消息

        v2.0: 使用官方 trim_messages 替代手写裁剪逻辑

        Returns:
            (保留的消息列表, 被裁剪的消息列表)
        """
        try:
            from langchain_core.messages import trim_messages, HumanMessage, AIMessage, SystemMessage

            # 转换为 LangChain 消息格式
            lc_messages = []
            for m in messages:
                role = m.get("role", "user")
                content = _content_to_str(m.get("content", ""))
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))

            # trim_messages: 保留最近的消息，裁剪旧的
            max_tokens = self.max_tokens - self.reserve_tokens

            def _token_counter(messages) -> int:
                """字符数近似 token 估算（约 2 字符 = 1 token）"""
                return sum(len(_content_to_str(m.content)) // 2 for m in messages)

            trimmed = trim_messages(
                lc_messages,
                max_tokens=max_tokens,
                token_counter=_token_counter,
                start_on="human",
                include_system=True,
                allow_partial=False,
            )

            # 找出被裁剪的消息
            trimmed_ids = {id(m) for m in trimmed}
            removed = [m for m in lc_messages if id(m) not in trimmed_ids]

            # 转回 dict 格式
            def _msg_to_dict(msg) -> dict:
                role = "system" if isinstance(msg, SystemMessage) else \
                       "assistant" if isinstance(msg, AIMessage) else "user"
                return {"role": role, "content": _content_to_str(msg.content)}

            return [_msg_to_dict(m) for m in trimmed], [_msg_to_dict(m) for m in removed]

        except ImportError:
            logger.warning("langchain_core trim_messages 不可用，降级为简单裁剪")
            return self._fallback_trim(messages)

    def _fallback_trim(self, messages: List[dict]) -> tuple:
        """降级裁剪（保留最近 N 条）"""
        if len(messages) <= self.keep_recent:
            return messages, []

        removed = messages[:-self.keep_recent]
        kept = messages[-self.keep_recent:]
        return kept, removed

    async def _generate_summary(self, messages: List[dict]) -> str:
        """用 LLM 生成对话摘要（v2.0: with_structured_output）"""
        text = "\n".join(f"[{m.get('role', 'user')}] {_content_to_str(m.get('content', ''))[:500]}" for m in messages)

        if not self.llm:
            return self._fallback_summary(messages)

        try:
            from app.agent.structured_schemas import CompactionSummary
            from langchain_core.messages import HumanMessage, SystemMessage

            structured_llm = self.llm.with_structured_output(CompactionSummary)
            result = await structured_llm.ainvoke([
                SystemMessage(content="你是一个对话压缩专家。"),
                HumanMessage(content=f"将以下对话压缩为结构化摘要。保留核心需求、关键决定、待办事项，丢弃寒暄。\n\n对话:\n{text[:8000]}"),
            ])

            parts = result.key_points
            if result.user_decisions:
                parts.extend(f"决定: {d}" for d in result.user_decisions)
            if result.pending_tasks:
                parts.extend(f"待办: {t}" for t in result.pending_tasks)
            return "\n".join(f"- {p}" for p in parts)

        except Exception as e:
            logger.warning(f"[compactor] LLM 摘要失败，降级: {e}")
            return self._fallback_summary(messages)

    def _fallback_summary(self, messages: List[dict]) -> str:
        """降级摘要"""
        user_msgs = [m for m in messages if m.get("role") == "user"]
        tool_msgs = [m for m in messages if m.get("role") == "tool"]

        parts = [f"共 {len(messages)} 条消息（{len(user_msgs)} 条用户消息，{len(tool_msgs)} 次工具调用）"]
        for m in user_msgs[-3:]:
            content = _content_to_str(m.get("content", ""))[:200]
            if content:
                parts.append(f"- 用户: {content}")

        return "\n".join(parts)

    async def _flush_important_memory(
        self, messages: List[dict], user_id: int, conversation_id: int
    ) -> None:
        """pre-flush: 将重要信息保存到长期记忆（异步入队）"""
        if not self.memory_manager:
            return

        try:
            # v5.1: 使用异步入队，不阻塞 compaction 流程
            await self.memory_manager.enqueue_summary(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=messages,
            )
            logger.info(f"[compactor] pre-flush: 长期记忆已入队(异步)")
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
