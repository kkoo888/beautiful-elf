"""Context Engine — 动态 Context 组装管道

替代 engine.py 中硬编码的系统提示，实现 Deep Agents 风格的
多源 Context 动态组装。

组装管道（按优先级）:
  1. 系统人格（soul_config）
  2. 用户偏好（user preferences）
  3. 长期记忆（MemoryManager 语义检索）
  4. RAG 知识库（RAGPipeline 检索）
  5. 技能上下文（命中技能时注入）
  6. 工具定义摘要（按意图动态选择）

设计原则:
  - 每个来源独立获取，失败时降级跳过
  - 总 token 预算控制，超出时按优先级裁剪
  - 不含路由细节，由 engine.py 调用
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)

# Context 预算（字符数，粗略估算 1 中文字 ≈ 2 token）
MAX_CONTEXT_CHARS = 6000


@dataclass
class ContextResult:
    """Context 组装结果"""
    system_prompt: str                          # 最终系统提示
    context_parts: Dict[str, str] = field(default_factory=dict)  # 各来源的上下文
    sources_used: List[str] = field(default_factory=list)        # 实际使用的来源
    total_chars: int = 0                        # 总字符数


class ContextEngine:
    """动态 Context 组装引擎"""

    def __init__(
        self,
        memory_manager=None,
        rag_pipeline=None,
        skill_executor=None,
    ):
        """
        Args:
            memory_manager: MemoryManager 实例（可选）
            rag_pipeline: RAGPipeline 实例（可选）
            skill_executor: SkillExecutor 实例（可选）
        """
        self.memory_manager = memory_manager
        self.rag_pipeline = rag_pipeline
        self.skill_executor = skill_executor

    async def assemble(
        self,
        user_id: int,
        conversation_id: int,
        user_message: str,
        intent: Optional[dict] = None,
        tools: Optional[List[dict]] = None,
        skill_context: Optional[str] = None,
    ) -> ContextResult:
        """
        组装完整的 Context。

        Args:
            user_id: 用户 ID
            conversation_id: 会话 ID
            user_message: 用户最新消息
            intent: 意图路由结果（可选）
            tools: 可用工具列表摘要（可选）
            skill_context: 技能上下文（命中技能时传入）

        Returns:
            ContextResult
        """
        parts: Dict[str, str] = {}
        budget_remaining = MAX_CONTEXT_CHARS

        # 1. 系统人格（最高优先级，不可裁剪）
        soul = self._build_soul_prompt(intent)
        parts["soul"] = soul
        budget_remaining -= len(soul)

        # 2. 技能上下文（命中技能时注入，高优先级）
        if skill_context:
            parts["skill"] = skill_context
            budget_remaining -= len(skill_context)

        # 3. 长期记忆（语义检索，中优先级）
        if self.memory_manager and user_message and budget_remaining > 500:
            memory_ctx = await self._retrieve_memory(user_id, user_message, budget=1500)
            if memory_ctx:
                parts["memory"] = memory_ctx
                budget_remaining -= len(memory_ctx)

        # 4. RAG 知识库（语义检索，中优先级）
        if self.rag_pipeline and self.rag_pipeline.is_ready and user_message and budget_remaining > 500:
            rag_ctx = await self._retrieve_knowledge(user_message, budget=2000)
            if rag_ctx:
                parts["knowledge"] = rag_ctx
                budget_remaining -= len(rag_ctx)

        # 5. 工具定义摘要（低优先级）
        if tools and budget_remaining > 300:
            tools_ctx = self._format_tool_defs(tools, budget=1000)
            if tools_ctx:
                parts["tools"] = tools_ctx
                budget_remaining -= len(tools_ctx)

        # 6. 意图信息（辅助）
        if intent and budget_remaining > 200:
            intent_ctx = self._format_intent(intent)
            if intent_ctx:
                parts["intent"] = intent_ctx
                budget_remaining -= len(intent_ctx)

        # 组装最终 system prompt
        system_prompt = self._compose_system_prompt(parts)

        return ContextResult(
            system_prompt=system_prompt,
            context_parts=parts,
            sources_used=list(parts.keys()),
            total_chars=len(system_prompt),
        )

    # ── 各来源组装 ──────────────────────────────────────

    def _build_soul_prompt(self, intent: Optional[dict] = None) -> str:
        """构建系统人格提示"""
        base = (
            "你是 Beautiful-Elf 智能助手，能够使用工具回答用户问题。\n"
            "请用中文回答，保持友好、专业的语气。"
        )

        # 如果命中技能，添加技能领域提示
        if intent and intent.get("intent_name") and intent["intent_name"] != "semantic_cache_hit":
            skill_name = intent.get("intent_name", "")
            base += f"\n当前激活技能：{skill_name}"

        return base

    async def _retrieve_memory(self, user_id: int, query: str, budget: int = 1500) -> str:
        """检索长期记忆"""
        try:
            memory_text = await self.memory_manager.search(
                query=query, user_id=user_id, limit=3,
            )
            if not memory_text:
                return ""

            # 裁剪到预算
            if len(memory_text) > budget:
                memory_text = memory_text[:budget] + "..."

            return f"【相关记忆】\n{memory_text}"
        except Exception as e:
            logger.warning(f"[context_engine] 记忆检索失败（降级跳过）: {e}")
            return ""

    async def _retrieve_knowledge(self, query: str, budget: int = 2000) -> str:
        """检索 RAG 知识库"""
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
        """格式化工具定义摘要"""
        if not tools:
            return ""

        lines = ["【可用工具】"]
        remaining = budget
        for t in tools:
            name = t.get("name", "")
            desc = t.get("description", "")
            line = f"- {name}: {desc}"
            if remaining - len(line) < 0:
                lines.append(f"- ...（共 {len(tools)} 个工具）")
                break
            lines.append(line)
            remaining -= len(line)

        return "\n".join(lines)

    def _format_intent(self, intent: dict) -> str:
        """格式化意图信息"""
        name = intent.get("intent_name", "")
        score = intent.get("score", 0)
        if not name or name == "semantic_cache_hit":
            return ""
        return f"【意图匹配】{name} (置信度: {score:.2f})"

    def _compose_system_prompt(self, parts: Dict[str, str]) -> str:
        """按优先级拼装最终 system prompt"""
        ordered_keys = ["soul", "skill", "intent", "memory", "knowledge", "tools"]
        sections = []
        for key in ordered_keys:
            if key in parts and parts[key]:
                sections.append(parts[key])
        return "\n\n".join(sections)
