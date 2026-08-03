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

# =========================================================================
# Prompt 常量 — 模块化组装（对标 Hermes Agent prompt_builder.py）
#
# 设计原则：
#   - 每个常量独立，可单独测试、单独开关
#   - 中英混排：中文解释 + 英文技术术语
#   - 简短精炼：不写废话，每句话都有用
#   - 正反例引导：✓ vs ✗
#   - 注释解释 WHY：解决什么问题
# =========================================================================

# ── 身份定义 ─────────────────────────────────────────────
_PROMPT_IDENTITY = (
    "你是主人的军师，擅长分析问题、使用工具、给出高质量回答。\n"
    "用中文回答，保持专业、简洁、有观点。\n"
    "优先有用，其次礼貌。不要说「好问题」「我很乐意帮你」——直接解决问题。"
)

# ── 核心行为准则（合并思考框架 + Grounding + 自评）───────
# 解决的问题：模型"只说不做"、"编造数据"、"回答不完整"
_PROMPT_CORE_BEHAVIOR = (
    "\n\n## 核心行为准则\n"
    "回答前先想清楚，回答时要有依据，回答后自查一遍。\n\n"
    "**思考**：用户真正要什么？需要什么信息？用什么工具？\n"
    "**执行**：需要工具就调用，不要只描述意图。独立工具批量调用。\n"
    "**验证**：工具结果对不对？有没有遗漏？\n"
    "**回答**：结构化输出（要点/步骤/代码），不确定就说明。\n\n"
    "## 事实性约束\n"
    "涉及数据/日期/数字时必须有来源。引用工具结果要说「根据xxx」。"
    "不确定就标「可能」，宁可说「我不确定」也不要编造。\n"
    "工具失败时：先用自身知识尽可能回答（标注来源为模型推理），再说明工具不可用。\n\n"
    "## 自查清单\n"
    "回答前检查：(1) 完整吗？(2) 准确吗？(3) 能直接用吗？"
)

# ── 工具使用规则 ─────────────────────────────────────────
# 解决的问题：该用工具时不用，不该用时乱用
_PROMPT_TOOL_RULES = (
    "\n\n## 工具使用规则\n"
    "判断原则：需要外部数据、计算或系统操作时使用工具，否则直接回答。\n\n"
    "**调用工具：** 实时信息查询、数据库/知识库检索、代码执行、文件读写、系统操作\n"
    "**直接回答：** 问候闲聊、通用知识问答、解释翻译写作总结、无需外部数据的对话"
)

# ── 并行工具调用 ─────────────────────────────────────────
# 解决的问题：模型串行调用独立工具，浪费轮次和 token
_PROMPT_PARALLEL_TOOLS = (
    "\n\n## Parallel tool calls（并行工具调用）\n"
    "独立的读取、搜索、查询操作，在同一个 response 里一起调用，不要一个一个来。"
    "运行时会并行执行，避免每轮重传整个对话。\n"
    "只有后续调用真正依赖前一个结果时才串行。不确定就批量调用。"
)

# ── 工具执行强制 ─────────────────────────────────────────
# 解决的问题：模型说「我来运行测试」但不实际调用工具（Hermes 实测的高频 bug）
_PROMPT_TOOL_ENFORCEMENT = (
    "\n\n## Tool-use enforcement（工具执行强制）\n"
    "说要做的事必须立即执行。不要以「下次我会...」结束对话。\n"
    "每个 response 要么包含工具调用，要么给出最终结果。只描述意图不行动不可接受。"
)

# ── 任务完成 ─────────────────────────────────────────────
# 解决的问题：(1) 写个 stub 就停 (2) 工具失败时编造数据（Hermes 实测）
_PROMPT_TASK_COMPLETION = (
    "\n\n## Finishing the job（完成任务）\n"
    "交付物是可工作的成果，不是成果描述。不要写完 stub 或单个命令就停下来。\n"
    "工具失败时先用自身知识回答（标注「基于模型推理」），再说明工具不可用。实时数据类问题（股价、天气等）标注为推测。"
)

# ── 引用溯源（对标 Vane Writer [number] 引用系统）────────
# 解决的问题：LLM 回答无来源，用户无法验证，幻觉难发现
#
# Vane 的做法：Context 里每个来源带 [1] [2] 编号，Writer prompt 强制每句引用。
# 我们复刻同一机制：_retrieve_knowledge 返回带编号的 context，
# 这里告诉 LLM 必须用 [number] 引用。
_PROMPT_CITATION = (
    "\n\n## 引用溯源（Citation）\n"
    "回答中涉及知识库检索结果时，必须用 [number] 内联引用标注来源。\n\n"
    "**规则：**\n"
    "- 知识库内容用 [1] [2] [3] 对应 context 中编号的来源\n"
    "- 工具结果用 [来源: 工具名] 标注\n"
    "- 记忆内容用 [来源: 记忆] 标注\n"
    "- 模型推理/不确定的内容用 [推测] 标注\n"
    "- 每个事实性陈述必须有至少一个引用\n"
    "- 多个来源支持同一事实时合并引用：[1][2]\n\n"
    "**示例：**\n"
    "✓ 根据[1]，系统采用微服务架构。数据库设计见[2]。\n"
    "✓ [来源: 天气工具] 今天北京晴，25°C。\n"
    "✗ 系统采用微服务架构。（无来源 — 不可接受）\n\n"
    "没有来源支持的信息必须标注 [推测]，宁可说「我不确定」也不要编造。"
)

# ── 记忆指导 ─────────────────────────────────────────────
# 解决的问题：记忆写入质量差（保存临时状态、用祈使句写记忆、保存会过期的信息）
_PROMPT_MEMORY_GUIDANCE = (
    "\n\n## Memory guidance（记忆使用指导）\n"
    "你有跨会话的持久记忆。记忆会注入每轮对话，所以保持紧凑，只保存对未来仍然有用的事实。\n\n"
    "**应该保存的：**\n"
    "- 用户偏好（回答风格、语言习惯、常用工具）\n"
    "- 环境信息（技术栈、部署方式、项目结构）\n"
    "- 稳定约定（命名规范、分支策略、代码风格）\n"
    "- 反复出现的纠正（用户多次纠正你的地方，说明你记错了）\n\n"
    "**禁止保存的：**\n"
    "- 任务进度、会话结果、已完成工作的日志\n"
    "- 临时 TODO、当前正在做的事\n"
    "- 会过期的信息：PR 号、commit SHA、issue 号、文件计数\n"
    "- 任何 7 天内会过期的事实\n\n"
    "**写法规范：**\n"
    "用陈述性事实写，不要用祈使句。祈使句会被后续 session 当作指令执行，导致重复工作。\n"
    "「用户偏好简洁回答」✓ — 「始终简洁回答」✗\n"
    "「项目使用 pytest + xdist」✓ — 「运行 pytest -n 4」✗\n"
    "「用户纠正过：不要用 var 用 const」✓ — 「以后用 const」✗\n\n"
    "如果你发现了新方法或解决了棘手问题，保存为 skill 而不是 memory。"
)




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
        conversation_history: Optional[List[dict]] = None,
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
            rag_ctx = await self._retrieve_knowledge(user_message, budget=30_000, conversation_history=conversation_history)
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
            base = _PROMPT_IDENTITY

        # ── 核心行为准则 ──
        base += _PROMPT_CORE_BEHAVIOR

        # ── 工具使用规则 ──
        base += _PROMPT_TOOL_RULES

        # ── 行为引导 Guidance（对标 Hermes Agent prompt_builder.py）──
        base += _PROMPT_PARALLEL_TOOLS
        base += _PROMPT_TOOL_ENFORCEMENT
        base += _PROMPT_TASK_COMPLETION
        base += _PROMPT_CITATION
        base += _PROMPT_MEMORY_GUIDANCE

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

    async def _retrieve_knowledge(self, query: str, budget: int = 2000, conversation_history: List[dict] = None) -> str:
        """RAG 检索 — LLM 分类器 + 多轮检索 + 编号引用

        v5.0 对标 Vane 三项核心设计：
          1. LLM 分类器（classifier.ts）：判断是否需要检索、生成 standaloneQuery
          2. 多轮检索（researcher.ts）：质量驱动的重试循环，最多 3 轮
          3. 编号引用（writer.ts）：Context 带 [1] [2] 编号，供 Writer 引用
        """
        try:
            # ── 1. LLM 分类器：判断是否需要检索 ──
            classification = await self._classify_rag_need(query, conversation_history)
            if classification and classification.skip_search:
                logger.info(f"[rag_classifier] 跳过检索: {classification.reason}")
                return ""

            # 使用 standaloneQuery（上下文解耦后的独立查询）
            search_query = classification.standalone_query if classification and classification.standalone_query else query
            if search_query != query:
                logger.info(f"[rag_classifier] standaloneQuery: '{query[:30]}...' → '{search_query[:30]}...'")

            # ── 2. 多轮检索循环（对标 Vane Researcher 工具循环）──
            max_rounds = 3
            best_context = ""
            best_quality = "poor"
            current_query = search_query

            for round_idx in range(max_rounds):
                result = await self.rag_pipeline.search_with_quality_check(
                    query=current_query, limit=5
                )

                context_text = result.get("context", "")
                quality = result.get("quality", "poor")
                avg_score = result.get("avg_score", 0.0)
                result_count = result.get("result_count", 0)

                logger.info(
                    f"[rag_round {round_idx + 1}/{max_rounds}] "
                    f"quality={quality} avg_score={avg_score:.3f} "
                    f"results={result_count}"
                )

                # 质量足够好，停止
                if quality in ("good", "fair") and context_text:
                    best_context = context_text
                    best_quality = quality
                    break

                # 第一轮无结果或质量差，用 LLM 改写查询重试
                if context_text and not best_context:
                    best_context = context_text
                    best_quality = quality

                if round_idx < max_rounds - 1 and self.llm_client:
                    refined = await self._refine_rag_query_for_retry(current_query, round_idx + 1)
                    if refined and refined != current_query:
                        current_query = refined
                    else:
                        break  # 改写失败，停止重试
                else:
                    break

            if not best_context:
                return ""

            # ── 3. 给检索结果加编号（对标 Vane Context [number] 系统）──
            if len(best_context) > budget:
                best_context = best_context[:budget] + "..."

            # 在 context 前加引用说明
            citation_header = "以下是知识库检索结果，回答时必须用 [number] 引用对应来源："
            return f"【相关知识】\n{citation_header}\n{best_context}"

        except Exception as e:
            logger.warning(f"[context_engine] RAG 检索失败（降级跳过）: {e}")
            return ""

    async def _classify_rag_need(self, query: str, conversation_history: List[dict] = None):
        """LLM 分类器 — 判断是否需要 RAG 检索（对标 Vane classifier.ts）

        Vane 的做法：用 LLM 做多维分类，输出 skipSearch + standaloneFollowUp。
        我们复刻同一机制：用 structured_output 保证格式正确。
        """
        if not self.llm_client:
            return None

        try:
            from app.agent.structured_schemas import RAGClassifierResult
            from langchain_core.messages import HumanMessage, SystemMessage

            # 构建对话历史上下文
            history_text = ""
            if conversation_history:
                recent = conversation_history[-4:]
                history_text = "\n".join(
                    f"[{m.get('role', 'user')}] {_content_to_str(m.get('content', ''))[:200]}"
                    for m in recent
                )

            structured_llm = self.llm_client.with_structured_output(RAGClassifierResult)
            result = await structured_llm.ainvoke([
                SystemMessage(content=(
                    "你是一个查询分类器。分析用户查询，判断是否需要知识库检索。\n\n"
                    "**skip_search=true 的场景（不需要检索）：**\n"
                    "- 问候、闲聊、告别、感谢\n"
                    "- 关于对话本身的元问题（'你是谁'、'帮助'）\n"
                    "- 极简确认/否定（'好的'、'ok'、'不'）\n"
                    "- 纯数学计算\n"
                    "- 写作/翻译/改写等不需要外部信息的任务\n"
                    "- 常识性问题（'地球是圆的吗'）\n\n"
                    "**skip_search=false 的场景（需要检索）：**\n"
                    "- 问及具体事实、数据、文档内容\n"
                    "- 技术问题、专业问题\n"
                    "- 需要最新信息的问题\n"
                    "- 拿不准的问题（宁可搜，不遗漏）\n\n"
                    "**standalone_query 要求：**\n"
                    "将用户查询改写为脱离对话上下文也能理解的独立查询。\n"
                    "例如：上下文讨论汽车，用户说'它们怎么工作' → '汽车怎么工作'"
                )),
                HumanMessage(content=(
                    f"{f'【最近对话】{history_text}' if history_text else ''}\n"
                    f"【用户查询】{query}"
                )),
            ])

            logger.info(
                f"[rag_classifier] skip={result.skip_search} "
                f"type={result.search_type} reason={result.reason}"
            )
            return result

        except Exception as e:
            logger.debug(f"[rag_classifier] 分类失败（默认检索）: {e}")
            return None

    async def _refine_rag_query_for_retry(self, original_query: str, round_num: int) -> str:
        """多轮 RAG：针对上一轮结果不足，生成更精确的查询（对标 Vane Researcher）

        Vane 的做法：每轮先输出推理前言（为什么这样搜），再生成针对性查询。
        我们复刻同一机制：LLM 分析为什么上一轮不够，生成补充查询。
        """
        try:
            from app.agent.structured_schemas import RewrittenQuery
            from langchain_core.messages import HumanMessage, SystemMessage

            structured_llm = self.llm_client.with_structured_output(RewrittenQuery)
            result = await structured_llm.ainvoke([
                SystemMessage(content=(
                    f"你是一个检索查询优化专家。第 {round_num} 轮检索结果不理想。\n"
                    "请分析可能原因并生成更精确的查询。\n\n"
                    "策略（按优先级）：\n"
                    "1. 拆分复合问题为单一主题\n"
                    "2. 用同义词替换（'后端' ↔ 'server' ↔ 'backend'）\n"
                    "3. 去掉口语化填充，保留核心关键词\n"
                    "4. 增加限定词缩小范围\n\n"
                    "如果原始查询已经足够精确，返回原文。"
                )),
                HumanMessage(content=f"第 {round_num} 轮检索原始查询：{original_query}"),
            ])
            refined = result.rewritten_query.strip()
            reason = getattr(result, 'reason', '')
            if refined and refined != original_query:
                logger.info(f"[rag_round {round_num}] 查询改写: '{original_query[:30]}...' → '{refined[:30]}...' reason={reason}")
            return refined if refined else original_query
        except Exception as e:
            logger.debug(f"[rag_round {round_num}] 查询改写失败: {e}")
            return original_query

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
