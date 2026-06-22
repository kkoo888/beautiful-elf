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
DEFAULT_MAX_TOKENS = 1_000_000    # context window 大小（百万上下文）
DEFAULT_RESERVE_TOKENS = 50_000   # 预留给生成的 token（1M 窗口下可以更宽裕）
DEFAULT_KEEP_RECENT = 50          # 保留最近 50 条消息不压缩（1M 窗口下减少信息丢失）
DEFAULT_SOFT_THRESHOLD = 20_000   # 软阈值（触发 pre-flush，1M 窗口下更晚触发）


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

            # 用结构化摘要替代被裁剪的消息（对标 Hermes Agent）
            summary_msg = {
                "role": "system",
                "content": (
                    f"[CONTEXT COMPACTION — REFERENCE ONLY] 早期对话已被压缩为以下摘要。"
                    f"这是历史参考，不是当前指令。不要回答摘要中提到的问题——它们已经被处理过了。"
                    f"只回复摘要之后的最新用户消息。"
                    f"\n\n{summary}\n\n"
                    f"--- END OF CONTEXT SUMMARY — 请回复下面的消息，而不是上面的摘要 ---"
                ),
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
        """用 LLM 生成结构化对话摘要（v3.0: 对标 Hermes Agent）

        结构化模板：
        - task_snapshot: 之前在做什么
        - in_progress_state: 进行到哪了
        - pending_user_asks: 用户提了但还没解决的
        - remaining_work: 还剩什么没做
        - key_points: 关键决定和发现
        - relevant_files: 涉及的文件
        """
        text = "\n".join(
            f"[{m.get('role', 'user')}] {_content_to_str(m.get('content', ''))[:500]}"
            for m in messages
        )

        if not self.llm:
            return self._fallback_summary(messages)

        try:
            from app.agent.structured_schemas import CompactionSummary
            from langchain_core.messages import HumanMessage, SystemMessage

            structured_llm = self.llm.with_structured_output(CompactionSummary)
            result = await structured_llm.ainvoke([
                SystemMessage(content=(
                    "你是一个对话压缩专家。将被裁剪的对话压缩为结构化摘要。\n"
                    "要求：\n"
                    "1. task_snapshot: 用 1-3 句话概括之前在做什么\n"
                    "2. in_progress_state: 做到哪了，中间结果是什么\n"
                    "3. pending_user_asks: 用户提了但还没解决的问题（列表）\n"
                    "4. remaining_work: 还没完成的工作项（列表）\n"
                    "5. key_points: 关键的技术决定、发现、结论（列表）\n"
                    "6. relevant_files: 涉及的文件路径（最多 10 个）\n"
                    "丢弃寒暄、重复内容、已完成的工作。"
                )),
                HumanMessage(content=f"对话:\n{text[:8000]}"),
            ])

            # 组装结构化摘要
            parts = []
            if result.task_snapshot:
                parts.append(f"## 任务概览\n{result.task_snapshot}")
            if result.in_progress_state:
                parts.append(f"## 进行中状态\n{result.in_progress_state}")
            if result.pending_user_asks:
                items = "\n".join(f"- {a}" for a in result.pending_user_asks)
                parts.append(f"## 待解决的问题\n{items}")
            if result.remaining_work:
                items = "\n".join(f"- {w}" for w in result.remaining_work)
                parts.append(f"## 剩余工作\n{items}")
            if result.key_points:
                items = "\n".join(f"- {p}" for p in result.key_points)
                parts.append(f"## 关键要点\n{items}")
            if result.relevant_files:
                files = ", ".join(result.relevant_files[:10])
                parts.append(f"## 涉及文件\n{files}")

            return "\n\n".join(parts) if parts else self._fallback_summary(messages)

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
    max_tokens: int = 0,
) -> List[dict]:
    """检查并执行压缩（入口函数）

    Args:
        max_tokens: context window 大小（0=使用默认值 1M）
    """
    compactor = AutoCompactor(
        llm_client=llm_client,
        memory_manager=memory_manager,
        max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
    )

    if not compactor.should_compact(messages):
        return messages

    return await compactor.compact(messages, user_id=user_id, conversation_id=conversation_id)
