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


@dataclass
class ContextResult:
    """Context 组装结果"""
    system_prompt: str
    context_parts: Dict[str, str] = field(default_factory=dict)
    sources_used: List[str] = field(default_factory=list)
    total_chars: int = 0


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

        # 4. 长期记忆
        if self.memory_manager and user_message and budget_remaining > 500:
            memory_ctx = await self._retrieve_memory(user_id, user_message, budget=1500)
            if memory_ctx:
                parts["memory"] = memory_ctx
                budget_remaining -= len(memory_ctx)

        # 5. RAG 知识库
        if self.rag_pipeline and getattr(self.rag_pipeline, 'is_ready', False) and user_message and budget_remaining > 500:
            rag_ctx = await self._retrieve_knowledge(user_message, budget=2000)
            if rag_ctx:
                parts["knowledge"] = rag_ctx
                budget_remaining -= len(rag_ctx)

        # 6. 工具定义摘要
        tool_list = tools or self.get_tool_summaries()
        if tool_list and budget_remaining > 300:
            tools_ctx = self._format_tool_defs(tool_list, budget=1000)
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
            "请用中文回答，保持友好、专业的语气。"
        )
        if intent and intent.get("intent_name") and intent["intent_name"] != "semantic_cache_hit":
            base += f"\n当前激活技能：{intent.get('intent_name', '')}"
        return base

    async def _retrieve_memory(self, user_id: int, query: str, budget: int = 1500) -> str:
        try:
            memory_text = await self.memory_manager.search(query=query, user_id=user_id, limit=3)
            if not memory_text:
                return ""
            if len(memory_text) > budget:
                memory_text = memory_text[:budget] + "..."
            return f"【相关记忆】\n{memory_text}"
        except Exception as e:
            logger.warning(f"[context_engine] 记忆检索失败（降级跳过）: {e}")
            return ""

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
            return ""
        lines = ["【可用工具】"]
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

        压缩策略:
          - 保留关键事实、数字、结论
          - 丢弃冗余描述、重复信息
          - 结构化输出（要点列表）
        """
        if len(text) <= target_chars:
            return text

        if not self.llm_client:
            # 无 LLM 时降级为截取（保留开头和结尾）
            half = target_chars // 2
            return text[:half] + "\n...(已压缩)...\n" + text[-half:]

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            response = await self.llm_client.ainvoke([
                SystemMessage(content=(
                    "你是一个信息压缩专家。将以下内容压缩到目标长度内，要求：\n"
                    "1. 保留所有关键事实、数字、结论\n"
                    "2. 丢弃冗余描述和重复信息\n"
                    "3. 用要点列表格式输出\n"
                    f"4. 目标长度：{target_chars} 字符以内"
                )),
                HumanMessage(content=text),
            ])
            compressed = response.content.strip()
            logger.info(f"[context_engine] 压缩: {len(text)} → {len(compressed)} 字符")
            return compressed

        except Exception as e:
            logger.warning(f"[context_engine] LLM 压缩失败，降级为截取: {e}")
            half = target_chars // 2
            return text[:half] + "\n...(已压缩)...\n" + text[-half:]

    # ── Query Rewriting（RAG 检索前改写）────────────────

    async def rewrite_query(self, user_query: str, conversation_history: List[dict] = None) -> str:
        """将口语化/模糊的用户查询改写为适合向量检索的精确查询

        场景:
          - "那个上次说的东西怎么弄" → 基于上下文补全具体指代
          - "帮我看看这个" → 结合上下文明确"这个"是什么
          - 口语化表达 → 转为更精确的技术描述
        """
        if not self.llm_client:
            return user_query

        # 构建上下文（最近 3 条对话）
        history_text = ""
        if conversation_history:
            recent = conversation_history[-3:]
            history_text = "\n".join(f"[{m.get('role', 'user')}] {m.get('content', '')}" for m in recent)

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            prompt = f"""将以下用户查询改写为适合向量检索的精确查询。

要求:
- 如果用户用了"这个""那个""它"等指代词，结合对话历史补全
- 如果是口语化表达，转为更精确的技术描述
- 如果查询已经足够精确，直接返回原文
- 只返回改写后的查询，不要解释

{f"【最近对话】{history_text}" if history_text else ""}

【用户查询】{user_query}"""

            response = await self.llm_client.ainvoke([
                SystemMessage(content="你是一个查询改写专家，只输出改写后的查询文本。"),
                HumanMessage(content=prompt),
            ])
            rewritten = response.content.strip()

            if rewritten and rewritten != user_query:
                logger.info(f"[context_engine] query rewriting: '{user_query[:30]}...' → '{rewritten[:30]}...'")
            return rewritten or user_query

        except Exception as e:
            logger.warning(f"[context_engine] query rewriting 失败，使用原始查询: {e}")
            return user_query
