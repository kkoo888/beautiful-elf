"""Context Engine — 动态 Context 组装管道（v2.2 新增压缩 + Query Rewriting）

功能:
  - get_tool_summaries() 方法（engine.py 调用）
  - RAG pipeline 注入支持
  - 工具结果 JSON 格式化
  - Context 压缩策略（LLM 驱动的智能压缩）
  - Query Rewriting（口语化查询改写为精确检索查询）
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import json

from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_CONTEXT_CHARS = 6000


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


@dataclass
class ContextResult:
    """Context 组装结果"""
    system_prompt: str
    context_parts: Dict[str, str] = field(default_factory=dict)
    sources_used: List[str] = field(default_factory=list)
    total_chars: int = 0
    # 记忆元数据（供 State 传递）
    memory_ids: List[str] = field(default_factory=list)
    memory_scores: List[float] = field(default_factory=list)
    memory_count: int = 0


class ContextEngine:
    """动态 Context 组装引擎（v2.2 — 新增压缩策略 + Query Rewriting）

    策略: Write → Select → Compress → Isolate
    """

    def __init__(
        self,
        memory_manager=None,
        rag_pipeline=None,
        tool_registry=None,
        llm_client=None,
    ):
        self.memory_manager = memory_manager
        self.rag_pipeline = rag_pipeline
        self.tool_registry = tool_registry
        self.llm_client = llm_client  # 用于压缩和 query rewriting

    def get_tool_summaries(self) -> List[dict]:
        """返回工具摘要列表（供 engine.py 使用）"""
        if self.tool_registry:
            return self.tool_registry.list_tool_summaries()
        return []

    async def assemble(
        self,
        user_id: int,
        conversation_id: int,
        user_message: str,
        intent: Optional[dict] = None,
        tools: Optional[List[dict]] = None,
        skill_context: Optional[str] = None,
    ) -> ContextResult:
        """组装完整的 Context（Write/Select/Compress/Isolate 四策略）"""
        parts: Dict[str, str] = {}
        budget_remaining = MAX_CONTEXT_CHARS

        # 1. 系统人格（最高优先级）
        soul = self._build_soul_prompt(intent)
        parts["soul"] = soul
        budget_remaining -= len(soul)

        # 2. 技能上下文
        if skill_context:
            parts["skill"] = skill_context
            budget_remaining -= len(skill_context)

        # 3. 用户偏好（从记忆中提取）
        if self.memory_manager and user_id and budget_remaining > 300:
            prefs = await self._retrieve_user_prefs(user_id, budget=500)
            if prefs:
                parts["preferences"] = prefs
                budget_remaining -= len(prefs)

        # 4. 长期记忆（user_message 已在 engine.py 中经过 query rewriting）
        memory_meta = {"ids": [], "scores": [], "count": 0}
        if self.memory_manager and user_message and budget_remaining > 500:
            memory_ctx, memory_meta = await self._retrieve_memory_with_meta(user_id, user_message, budget=1500)
            if memory_ctx:
                parts["memory"] = memory_ctx
                budget_remaining -= len(memory_ctx)

        # 5. RAG 知识库
        if self.rag_pipeline and getattr(self.rag_pipeline, 'is_ready', False) and user_message and budget_remaining > 500:
            rag_ctx = await self._retrieve_knowledge(user_message, budget=2000)
            if rag_ctx:
                parts["knowledge"] = rag_ctx
                budget_remaining -= len(rag_ctx)

        # 6. 工具定义摘要（根据意图动态过滤）
        tool_list = tools or self.get_tool_summaries()
        if tool_list and budget_remaining > 300:
            # 根据意图过滤工具
            filtered_tools = self._filter_tools_by_intent(tool_list, intent)
            tools_ctx = self._format_tool_defs(filtered_tools, budget=1000)
            if tools_ctx:
                parts["tools"] = tools_ctx
                budget_remaining -= len(tools_ctx)

        # 7. 意图信息
        if intent and budget_remaining > 200:
            intent_ctx = self._format_intent(intent)
            if intent_ctx:
                parts["intent"] = intent_ctx

        system_prompt = self._compose_system_prompt(parts)

        return ContextResult(
            system_prompt=system_prompt,
            context_parts=parts,
            sources_used=list(parts.keys()),
            total_chars=len(system_prompt),
            memory_ids=memory_meta.get("ids", []),
            memory_scores=memory_meta.get("scores", []),
            memory_count=memory_meta.get("count", 0),
        )

    async def _retrieve_user_prefs(self, user_id: int, budget: int = 500) -> str:
        """检索用户偏好（从长期记忆中提取偏好类记忆）"""
        try:
            if not self.memory_manager:
                return ""
            results = await self.memory_manager.search_with_scores(
                query="用户偏好 设置 风格 语言",
                user_id=user_id,
                limit=3,
            )
            if not results:
                return ""
            prefs = []
            for r in results:
                if r.get("type") == "user_memory" and r.get("summary"):
                    prefs.append(r["summary"])
            if not prefs:
                return ""
            text = "、".join(prefs[:3])
            if len(text) > budget:
                text = text[:budget] + "..."
            return f"【用户偏好】{text}"
        except Exception as e:
            logger.debug(f"[context_engine] 用户偏好检索失败（降级跳过）: {e}")
            return ""

    def _build_soul_prompt(self, intent: Optional[dict] = None) -> str:
        base = (
            "你是 Beautiful-Elf 智能助手，能够使用工具回答用户问题。\n"
            "请用中文回答，保持友好、专业的语气。\n\n"
            "## 工具使用规则\n"
            "你有一组可用工具，但不是每个问题都需要用工具。请严格遵守以下规则：\n\n"
            "**必须使用工具的情况：**\n"
            "- 用户明确要求搜索、查询、计算、执行代码、读写文件\n"
            "- 需要实时信息（天气、新闻、股票等）\n"
            "- 需要查询数据库或知识库\n"
            "- 用户的问题涉及外部数据或系统操作\n\n"
            "**禁止使用工具的情况：**\n"
            "- 问候、闲聊、告别、感谢（如「你好」「谢谢」「再见」）\n"
            "- 通用知识问答（你自己能回答的问题）\n"
            "- 简单的解释、翻译、写作、总结\n"
            "- 用户没有明确需要外部数据或工具辅助的对话\n\n"
            "**判断原则：** 先思考「这个问题我自己能回答吗？」如果能，直接回答，不要调用工具。"
            "只有当问题确实需要外部数据、计算或系统操作时，才使用工具。"
        )
        if intent and intent.get("intent_name") and intent["intent_name"] not in ("semantic_cache_hit", "chitchat"):
            base += f"\n\n当前激活技能：{intent.get('intent_name', '')}"
        return base

    def _filter_tools_by_intent(self, tools: List[dict], intent: Optional[dict]) -> List[dict]:
        """根据意图过滤工具列表（B+C 重构后，工具过滤已在 engine 层完成，此处直接透传）"""
        return tools

    async def _retrieve_memory_with_meta(
        self, user_id: int, query: str, budget: int = 1500
    ) -> tuple:
        """检索记忆并返回元数据（用于 State 传递）

        Returns:
            (formatted_text, metadata_dict)
            metadata_dict: {"ids": [...], "scores": [...], "count": int}
        """
        meta = {"ids": [], "scores": [], "count": 0}
        try:
            results = await self.memory_manager.search_with_scores(query=query, user_id=user_id, limit=3)
            if not results:
                return "", meta

            # 收集元数据
            meta["ids"] = [r.get("id", "") for r in results]
            meta["scores"] = [r.get("score", 0) for r in results]
            meta["count"] = len(results)

            # 格式化文本（复用 search() 的逻辑）
            parts = []
            for r in results:
                ptype = r.get("type", "detail")
                score = r.get("score", 0)
                if ptype in ("summary", "user_memory"):
                    parts.append(f"[记忆 | 相关度:{score:.2f} | {r.get('saved_at', '')}] {r.get('summary', '')}")
                else:
                    msg_count = len(r.get("messages", []))
                    parts.append(f"[对话记录 | 相关度:{score:.2f} | {r.get('saved_at', '')} | {msg_count}条消息]")

            text = "\n".join(parts)
            if len(text) > budget:
                text = text[:budget] + "..."
            return f"【相关记忆】\n{text}", meta
        except Exception as e:
            logger.warning(f"[context_engine] 记忆检索失败（降级跳过）: {e}")
            return "", meta

    async def _retrieve_knowledge(self, query: str, budget: int = 2000) -> str:
        try:
            knowledge_text = await self.rag_pipeline.search(query=query, limit=3)
            if not knowledge_text:
                return ""
            if len(knowledge_text) > budget:
                knowledge_text = knowledge_text[:budget] + "..."
            return f"【相关知识】\n{knowledge_text}"
        except Exception as e:
            logger.warning(f"[context_engine] RAG 检索失败（降级跳过）: {e}")
            return ""

    def _format_tool_defs(self, tools: List[dict], budget: int = 1000) -> str:
        if not tools:
            return "【可用工具】本次对话无需使用工具，请直接回答。"
        lines = ["【本次可用工具】以下是你可以使用的工具列表，请根据用户问题决定是否需要调用："]
        remaining = budget
        for t in tools:
            name = t.get("name", "")
            desc = t.get("description", "")
            risk = t.get("risk", "low")
            line = f"- {name} [{risk}]: {desc}"
            if remaining - len(line) < 0:
                lines.append(f"- ...（共 {len(tools)} 个工具）")
                break
            lines.append(line)
            remaining -= len(line)
        return "\n".join(lines)

    def _format_intent(self, intent: dict) -> str:
        name = intent.get("intent_name", "")
        score = intent.get("score", 0)
        if not name or name == "semantic_cache_hit":
            return ""
        return f"【意图匹配】{name} (置信度: {score:.2f})"

    def _compose_system_prompt(self, parts: Dict[str, str]) -> str:
        ordered_keys = ["soul", "skill", "intent", "preferences", "memory", "knowledge", "tools"]
        sections = [parts[k] for k in ordered_keys if k in parts and parts[k]]
        return "\n\n".join(sections)

    @staticmethod
    def format_tool_result(result: Any) -> str:
        """格式化工具结果为 JSON 字符串（非 Python repr）"""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, default=str)
        if isinstance(result, (list, tuple)):
            return json.dumps(result, ensure_ascii=False, default=str)
        return str(result)

    # ── Context 压缩（LLM 驱动）─────────────────────────

    async def compress_context(self, text: str, target_chars: int = 2000) -> str:
        """用 LLM 将长文本压缩到目标长度，保留核心信息

        v2.3: 优先使用 LlamaIndex SentenceSplitter 分块 + LLM 摘要
        压缩策略:
          - 保留关键事实、数字、结论
          - 丢弃冗余描述、重复信息
          - 结构化输出（要点列表）
        """
        if len(text) <= target_chars:
            return text

        if not self.llm_client:
            half = target_chars // 2
            return text[:half] + "\n...(已压缩)...\n" + text[-half:]

        try:
            # v2.3: 先用 LlamaIndex SentenceSplitter 分块，再 LLM 摘要
            # 这样压缩更精准（按语义边界分割，而非随机截断）
            from langchain_core.messages import HumanMessage, SystemMessage

            # 如果文本很长，先分块再压缩（避免超出 LLM context window）
            chunk_for_llm = text
            if len(text) > 8000:
                try:
                    from llama_index.core.node_parser import SentenceSplitter
                    splitter = SentenceSplitter(chunk_size=4000, chunk_overlap=200)
                    chunks = splitter.split_text(text)
                    # 取首尾两个 chunk（通常包含最重要信息）
                    chunk_for_llm = chunks[0] + "\n...\n" + chunks[-1] if len(chunks) > 1 else chunks[0]
                except ImportError:
                    chunk_for_llm = text[:4000] + "\n...\n" + text[-2000:]

            response = await self.llm_client.ainvoke([
                SystemMessage(content=(
                    "你是一个信息压缩专家。将以下内容压缩到目标长度内，要求：\n"
                    "1. 保留所有关键事实、数字、结论\n"
                    "2. 丢弃冗余描述和重复信息\n"
                    "3. 用要点列表格式输出\n"
                    f"4. 目标长度：{target_chars} 字符以内"
                )),
                HumanMessage(content=chunk_for_llm),
            ])
            compressed = _content_to_str(response.content).strip()
            logger.info(f"[context_engine] 压缩: {len(text)} → {len(compressed)} 字符")
            return compressed

        except Exception as e:
            logger.warning(f"[context_engine] LLM 压缩失败，降级为截取: {e}")
            half = target_chars // 2
            return text[:half] + "\n...(已压缩)...\n" + text[-half:]

    # ── Query Rewriting（RAG 检索前改写）────────────────

    async def rewrite_query(self, user_query: str, conversation_history: List[dict] = None) -> str:
        """将口语化/模糊的用户查询改写为适合向量检索的精确查询

        v2.3: with_structured_output(RewrittenQuery) 替代手动解析
        """
        if not self.llm_client:
            return user_query

        history_text = ""
        if conversation_history:
            recent = conversation_history[-3:]
            history_text = "\n".join(f"[{m.get('role', 'user')}] {_content_to_str(m.get('content', ''))}" for m in recent)

        try:
            from app.agent.structured_schemas import RewrittenQuery
            from langchain_core.messages import HumanMessage, SystemMessage

            structured_llm = self.llm_client.with_structured_output(RewrittenQuery)
            result = await structured_llm.ainvoke([
                SystemMessage(content="你是一个查询改写专家。"),
                HumanMessage(content=(
                    f"将以下用户查询改写为适合向量检索的精确查询。\n\n"
                    f"要求:\n- 指代词结合对话历史补全\n- 口语化转为精确技术描述\n- 已足够精确则返回原文\n\n"
                    f"{f'【最近对话】{history_text}' if history_text else ''}\n\n"
                    f"【用户查询】{user_query}"
                )),
            ])

            rewritten = result.rewritten_query.strip()
            if rewritten and rewritten != user_query:
                logger.info(f"[context_engine] query rewriting: '{user_query[:30]}...' → '{rewritten[:30]}...'")
            return rewritten or user_query

        except Exception as e:
            logger.warning(f"[context_engine] query rewriting 失败，使用原始查询: {e}")
            return user_query
