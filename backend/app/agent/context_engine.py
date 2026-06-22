"""Context Engine — 动态 Context 组装管道（v2.3 新增 Injection Guard + Budget）

功能:
  - get_tool_summaries() 方法（engine.py 调用）
  - RAG pipeline 注入支持
  - 工具结果 JSON 格式化
  - Context 压缩策略（LLM 驱动的智能压缩）
  - Query Rewriting（口语化查询改写为精确检索查询）
  - Injection Guard: 所有外部内容用 <untrusted> 标签包裹（v2.3）
  - Result Budget: 动态裁剪超长结果（v2.3）
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import json

from app.core.logging import get_logger
from app.agent.injection_guard import wrap_untrusted, detect_injection_attempt

logger = get_logger(__name__)

# MAX_CONTEXT_CHARS 由 context_length 动态计算
# 默认值：context_length 的 8%（约 80K 字符 @ 1M 窗口）
_DEFAULT_CONTEXT_LENGTH = 1_000_000
_CONTEXT_RATIO = 0.08  # system prompt 占 context window 的比例
# 模块级 fallback（nodes.py 导入用，实例化后会被 self._max_context_chars 覆盖）
MAX_CONTEXT_CHARS = int(_DEFAULT_CONTEXT_LENGTH * _CONTEXT_RATIO * 4)


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
        context_length: int = 0,
    ):
        self.memory_manager = memory_manager
        self.rag_pipeline = rag_pipeline
        self.tool_registry = tool_registry
        self.llm_client = llm_client  # 用于压缩和 query rewriting
        self._soul_prompt_cache: Optional[str] = None  # 用户配置的人格 prompt
        # 动态计算 context 预算（从 DB context_length 推导）
        _ctx = context_length or _DEFAULT_CONTEXT_LENGTH
        self._max_context_chars = int(_ctx * _CONTEXT_RATIO * 4)  # 4 chars/token

    def get_tool_summaries(self) -> List[dict]:
        """返回工具摘要列表（供 engine.py 使用）"""
        if self.tool_registry:
            return self.tool_registry.list_tool_summaries()
        return []

    def set_soul_prompt(self, prompt: str) -> None:
        """设置人格 prompt（用户配置变更时调用）"""
        self._soul_prompt_cache = prompt
        logger.info(f"[context_engine] 人格 prompt 已更新 ({len(prompt)} 字)")

    async def load_soul_prompt(self, db) -> None:
        """从数据库加载活跃的人格配置（启动时调用）"""
        try:
            from app.services.soul_config_service import SoulConfigService
            service = SoulConfigService()
            config = await service.get_active_soul_config(db)
            if config:
                self._soul_prompt_cache = self._compose_soul_prompt(config)
                logger.info(f"[context_engine] 已加载人格配置: {config.name}")
            else:
                logger.info("[context_engine] 无人格配置，使用默认")
        except Exception as e:
            logger.warning(f"[context_engine] 加载人格配置失败: {e}")

    @staticmethod
    def _compose_soul_prompt(config) -> str:
        """从 SoulConfig 结构化字段组装 prompt（对标 CrewAI role+goal+backstory 三要素）

        角色深度增强:
          - role: name + personality（身份定位）
          - goal: 从 background 中提取或使用默认目标（驱动决策方向）
          - backstory: background 字段（丰富角色人格）
          - speaking_style: 说话风格约束
        """
        # 优先使用自定义 system_prompt
        if config.system_prompt and config.system_prompt.strip():
            return config.system_prompt.strip()

        # 否则从结构化字段组装（对标 CrewAI role+goal+backstory 三要素）
        parts = []
        if config.name:
            parts.append(f"你是{config.name}。")
        if config.personality:
            traits = config.personality if isinstance(config.personality, list) else []
            if traits:
                parts.append(f"你的性格{'又'.join(traits)}。")
        if config.speaking_style:
            parts.append(f"说话风格：{config.speaking_style}。")
        # goal: 明确目标驱动（CrewAI 核心要素）
        parts.append("你的核心目标是：理解用户需求的本质，提供准确、深入、可操作的回答。")
        # backstory: background 字段作为背景故事
        if config.background:
            parts.append(f"背景：{config.background}")
        return "".join(parts) if parts else ""

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
        budget_remaining = self._max_context_chars

        # 1. 系统人格（最高优先级）
        soul = self._build_soul_prompt(intent)
        parts["soul"] = soul
        budget_remaining -= len(soul)

        # 2. 技能上下文
        if skill_context:
            parts["skill"] = skill_context
            budget_remaining -= len(skill_context)

        # 3. 用户偏好（从记忆中提取）
        if self.memory_manager and user_id and budget_remaining > 1000:
            prefs = await self._retrieve_user_prefs(user_id, budget=3_000)
            if prefs:
                parts["preferences"] = prefs
                budget_remaining -= len(prefs)

        # 4. 长期记忆（user_message 已在 engine.py 中经过 query rewriting）
        memory_meta = {"ids": [], "scores": [], "count": 0}
        if self.memory_manager and user_message and budget_remaining > 2000:
            memory_ctx, memory_meta = await self._retrieve_memory_with_meta(user_id, user_message, budget=15_000)
            if memory_ctx:
                parts["memory"] = memory_ctx
                budget_remaining -= len(memory_ctx)

        # 5. RAG 知识库
        if self.rag_pipeline and getattr(self.rag_pipeline, 'is_ready', False) and user_message and budget_remaining > 2000:
            rag_ctx = await self._retrieve_knowledge(user_message, budget=30_000)
            if rag_ctx:
                parts["knowledge"] = rag_ctx
                budget_remaining -= len(rag_ctx)

        # 6. 工具定义摘要（根据意图动态过滤）
        tool_list = tools or self.get_tool_summaries()
        if tool_list and budget_remaining > 1000:
            # 根据意图过滤工具
            filtered_tools = self._filter_tools_by_intent(tool_list, intent)
            tools_ctx = self._format_tool_defs(filtered_tools, budget=5_000)
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
        # 优先使用用户配置的人格
        if self._soul_prompt_cache:
            base = self._soul_prompt_cache
        else:
            base = (
                "你是主人的军师，擅长分析问题、使用合适的工具、给出高质量回答。\n"
                "请用中文回答，保持友好、专业的语气。"
            )

        # ── P0: ReAct + CoT 思考框架 ──
        base += (
            "\n\n## 思考方式\n"
            "回答前，请按以下步骤思考，然后总结回答：\n\n"
            "**Thought**：分析用户的真实意图，判断需要什么信息或工具\n"
            "**Action**：如果需要工具，选择最合适的工具并说明调用理由（框架会自动执行工具调用）\n"
            "**Observation**：检查工具返回的结果是否正确、完整\n"
            "**Answer**：基于所有信息，给出结构化的最终回答\n\n"
            "## 输出规范\n"
            "- 回答要有结构：使用要点列表、分步骤、标题分隔，避免大段纯文字\n"
            "- 需要工具时，先简要说明你要做什么，再调用工具\n"
            "- 不确定时明确说明不确定性，不要编造\n"
            "- 涉及数据/事实时，给出来源或依据\n"
            "- 长任务分步骤执行，每步完成后汇报进展\n"
        )

        # ── P0: 深度推理框架 ──
        base += (
            "\n\n## 深度推理框架\n"
            "对于复杂问题，请在回答前先完成以下思考：\n\n"
            "1. **核心挑战**: 这个问题最难的部分是什么？\n"
            "2. **关键要素**: 需要关注哪些关键信息？\n"
            "3. **潜在风险**: 有什么容易出错的地方？\n"
            "4. **执行策略**: 用什么方法解决这个问题？\n\n"
            "将以上思考作为内部推理过程，然后给出最终回答。\n"
        )

        # ── P0: 自评机制 ──
        base += (
            "\n\n## 自评清单（回答前自查）\n"
            "生成最终回答前，请按以下维度自查：\n\n"
            "1. **完整性**：是否覆盖了用户问题的所有方面？有无遗漏？\n"
            "2. **准确性**：信息是否准确？是否有依据支撑？有无编造？\n"
            "3. **可用性**：回答是否可直接使用？建议是否可操作？\n\n"
            "如果自查发现明显不足，请继续补充最终回答。\n"
        )

        # ── P0: Grounding 指令（幻觉消除 — 知识 grounding）──
        base += (
            "\n\n## 事实性约束（Grounding）\n"
            "- 涉及数据/日期/人名/数字时，必须给出来源或依据\n"
            "- 如果使用了工具结果或检索到的知识，明确引用（如「根据检索结果」「工具返回显示」）\n"
            "- 不确定的信息必须标明（如「据我了解」「可能」），不要伪装成确定事实\n"
            "- 如果没有可靠来源，宁可说「我不确定」也不要编造\n"
        )

        # 工具使用规则（始终追加）
        base += (
            "\n\n## 工具使用规则\n"
            "判断原则：需要外部数据、计算或系统操作时使用工具，否则直接回答。\n\n"
            "**调用工具：** 实时信息查询、数据库/知识库检索、代码执行、文件读写、系统操作\n"
            "**直接回答：** 问候闲聊、通用知识问答、解释翻译写作总结、无需外部数据的对话"
        )

        # 并行工具调用 Guidance（降低成本 + 延迟）
        base += (
            "\n\n## Parallel tool calls（并行工具调用）\n"
            "当你需要多个互不依赖的信息时，在同一个 response 里一起调用，"
            "而不是一个一个来。独立的读取、搜索、web fetch、只读命令应该"
            "批量放入同一个 assistant turn —— 运行时会并行执行独立调用，"
            "批量调用避免了每轮重传整个对话。\n"
            "只有当后续调用真正依赖前一个调用的结果时才串行（比如你必须先"
            "读文件才能改它）。如果不确定是否独立，就批量调用。"
        )


        # ── 工具执行强制（防止"只说不做"）──
        base += (
            "\n\n## Tool-use enforcement（工具执行强制）\n"
            "你必须使用工具来执行操作，而不是描述你打算做什么。"
            "当你说要执行某个操作（如「我来运行测试」「让我查一下文件」），"
            "你必须在同一个 response 里立即发起对应的工具调用。"
            "不要以「下次我会...」结束对话 —— 现在就执行。\n"
            "持续工作直到任务真正完成。不要只总结下一步计划就停下来。"
            "每个 response 应该要么 (a) 包含推进进度的工具调用，"
            "要么 (b) 给出最终结果。只描述意图而不行动的 response 不可接受。"
        )

        # ── 任务完成强制（防止"写个 stub 就停"和"编造结果"）──
        base += (
            "\n\n## Finishing the job（完成任务）\n"
            "当用户要求你构建、运行或验证某件事时，交付物是真正可工作的成果，"
            "而不是成果的描述。不要写了 stub、计划或单个命令就停下来，"
            "持续工作直到你实际运行了代码或产出了请求的结果。\n"
            "如果工具、安装或网络调用失败并阻塞了路径，直接说明并尝试替代方案。"
            "绝对不要用看起来合理的编造数据（假地址、假 JSON、假数字）"
            "替代你无法实际产出的结果。诚实地报告阻塞永远比编造结果更好。"
        )

        # ── 记忆使用指导（规范记忆写入质量）──
        base += (
            "\n\n## Memory guidance（记忆使用指导）\n"
            "你有跨会话的持久记忆。用记忆工具保存持久事实：用户偏好、环境信息、"
            "工具特性、稳定约定。记忆会注入每轮对话，所以保持紧凑，"
            "只保存对未来仍然有用的事实。\n"
            "不要保存任务进度、会话结果、已完成工作的日志或临时 TODO；"
            "这些从历史记录中召回。\n"
            "写记忆用陈述性事实，而不是对自己的指令。\n"
            "「用户偏好简洁回答」✓ — 「始终简洁回答」✗\n"
            "「项目使用 pytest + xdist」✓ — 「运行 pytest -n 4」✗"
        )

        if intent and intent.get("intent_name") and intent["intent_name"] not in ("semantic_cache_hit", "chitchat"):
            intent_name = intent.get("intent_name", "")
            base += f"\n\n当前激活技能：{intent_name}，请优先使用与该技能相关的工具完成任务。"
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
            results = await self.memory_manager.search_with_scores(query=query, user_id=user_id, limit=10)
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
                elif ptype == "reflexion":
                    # Reflexion 经验优先展示
                    parts.append(f"[历史反思 | 相关度:{score:.2f}] {r.get('summary', '')}")
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
        """格式化工具结果为 JSON 字符串（非 Python repr）

        v2.3: 外部内容用 <untrusted> 标签包裹，防止注入攻击
        """
        if isinstance(result, str):
            content = result
        elif isinstance(result, dict):
            content = json.dumps(result, ensure_ascii=False, default=str)
        elif isinstance(result, (list, tuple)):
            content = json.dumps(result, ensure_ascii=False, default=str)
        else:
            content = str(result)

        # 注入检测（仅记录日志，不阻断）
        if detect_injection_attempt(content):
            logger.warning("[context_engine] 检测到工具结果中疑似注入模式")

        return wrap_untrusted(content, source="tool_result")

    # ── Context 压缩（LLM 驱动）─────────────────────────

    async def compress_context(self, text: str, target_chars: int = 5000) -> str:
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
            if len(text) > 10000:
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
                    f"4. 目标长度：约{target_chars} 个汉字以内"
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
                SystemMessage(content="你是一个查询改写专家。将口语化、模糊的用户查询改写为适合向量检索的精确查询，同时保留原始语义。"),
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
