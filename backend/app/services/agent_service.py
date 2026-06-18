"""Agent 业务服务 — v4.3 完整版

v4.3 变更:
  1. [P0] 流式对话改用 astream_events(version="v3") — LangGraph 官方 Event Streaming API
     · typed projection，messages/values/output 独立消费，天然去重
     · 文档: https://docs.langchain.com/oss/python/langgraph/event-streaming
  2. [P0] AgentState 从 Pydantic BaseModel 迁移到 TypedDict（LangGraph 官方推荐）
v4.2 变更:
  1. [P0] 初始化加 asyncio.Lock 防竞态
  2. [P2] LLM 缓存加 TTL 过期机制
"""
import asyncio
import time
import uuid
from typing import Optional, AsyncIterator, Dict, Any

from app.core.logging import get_logger
from app.agent.state import _content_blocks_to_str

logger = get_logger(__name__)


class AgentService:
    """Agent 业务服务（v4.2）"""

    def __init__(self):
        self._graph = None
        self._context_engine = None  # 供外部刷新人格缓存
        self._provider_id: Optional[int] = None
        self._model_name: str = ""
        self._initialized = False
        self._enable_interrupt = False
        self._tool_stats: Dict[str, Dict] = {}  # 工具使用统计
        self._init_lock = asyncio.Lock()  # [P1] 防止并发初始化竞态

    @property
    def is_ready(self) -> bool:
        return self._graph is not None

    async def refresh_soul_prompt(self, db) -> None:
        """刷新人格 prompt 缓存（用户更新 soul_config 时调用）"""
        if self._context_engine:
            await self._context_engine.load_soul_prompt(db)
            logger.info("[agent_service] 人格 prompt 已刷新")

    async def initialize(
        self,
        db,
        provider_id: int,
        model_name: str = "",
        tool_names: Optional[list] = None,
        enable_interrupt: bool = False,
    ) -> bool:
        """初始化 Agent 引擎（v5.0 — 不再全量 bind_tools）

        B+C 架构: LLM 初始化时不绑定工具，每次请求由 engine 动态选择。
        """
        from app.agent.llm_service import llm_service
        from app.agent.tool_registry import tool_registry
        from app.agent.engine import build_agent_graph
        from app.agent.context_engine import ContextEngine
        from app.agent.skill_executor import skill_executor
        from app.services.memory_service import memory_service
        from app.services.intent_service import intent_service

        try:
            await tool_registry.load_from_db(db)

            # ── B+C: LLM 不再 bind_tools，工具由 engine 动态绑定 ──
            llm = await llm_service.get_chat_llm(
                db, provider_id=provider_id, model_name=model_name, bind_tools=None,
            )

            # ── 模型路由──
            from app.router.model_selector import ModelSelector
            model_selector = ModelSelector(default_model=model_name)
            # tier → 模型映射（对齐 router.runtime.yaml tier_mapping，后续从 DB 读取）
            # 默认全部走同一个模型，主人在 DB 配置不同模型后可切换
            model_selector.register_tier("S", model_name)  # R0 轻量（闲聊/简单问答）
            model_selector.register_tier("M", model_name)  # R1 标准（一般对话和任务）
            model_selector.register_tier("L", model_name)  # R2 强力（推理/调试/多步任务）
            model_selector.register_tier("XL", model_name)  # R3 最强（架构/高风险决策）
            # 注册 LLM 实例（get_llm 时使用）
            model_selector.register_llm(model_name, llm)

            memory_manager = memory_service.memory_manager
            intent_router = intent_service.intent_router

            # RAG pipeline 注入
            rag_pipeline = None
            try:
                from app.agent.rag_pipeline import RAGPipeline
                rag_pipeline = RAGPipeline(
                    embedding_model=None,  # 由 RAGPipeline 内部初始化
                )
                logger.info("RAG pipeline 已注入 ContextEngine")
            except Exception as e:
                logger.warning(f"RAG pipeline 初始化跳过: {e}")

            context_engine = ContextEngine(
                memory_manager=memory_manager,
                rag_pipeline=rag_pipeline,
                tool_registry=tool_registry,
            )

            # 加载用户配置的人格
            try:
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as soul_db:
                    await context_engine.load_soul_prompt(soul_db)
            except Exception as e:
                logger.warning(f"人格配置加载跳过: {e}")

            self._context_engine = context_engine

            self._enable_interrupt = enable_interrupt
            self._graph = build_agent_graph(
                llm=llm,
                tool_registry=tool_registry,
                context_engine=context_engine,
                memory_manager=memory_manager,
                intent_router=intent_router,
                skill_executor=skill_executor,
                rag_pipeline=rag_pipeline,
                model_selector=model_selector,
                enable_interrupt=enable_interrupt,
            )
            self._provider_id = provider_id
            self._model_name = model_name
            self._initialized = True

            logger.info(f"Agent 引擎初始化完成 (provider={provider_id}, model={model_name}, ML路由={model_selector.is_ml_available}, B+C动态工具, interrupt={enable_interrupt})")
            return True

        except ImportError as e:
            logger.warning(f"缺少 LangChain 依赖，Agent 降级: {e}")
            self._graph = None
            return False
        except Exception as e:
            logger.error(f"Agent 引擎初始化失败: {e}", exc_info=True)
            self._graph = None
            return False

    def _get_thread_id(self, conversation_id: int) -> str:
        """生成 thread_id（用于 checkpointer 状态追踪）"""
        return f"conv-{conversation_id}"

    def _get_config(self, conversation_id: int) -> dict:
        """获取 LangGraph config（含 thread_id）"""
        return {"configurable": {"thread_id": self._get_thread_id(conversation_id)}}

    async def chat(
        self,
        conversation_id: int,
        user_id: int,
        messages: list,
        provider_id: int = 0,
        model_name: str = "",
    ) -> Dict[str, Any]:
        """Agent 非流式对话"""
        if not self.is_ready:
            success = await self._lazy_init(provider_id, model_name)
            if not success:
                raise RuntimeError("Agent 引擎初始化失败")

        t0 = time.time()

        initial_state = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "messages": messages,
            "context": "",
            "system_prompt": "",
            "tool_calls": [],
            "tools_used": [],
            "final_answer": None,
            "iterations": 0,
            "needs_approval": False,
            "pending_tool_call": None,
            "intent": None,
            "skill_answer": None,
            "error": None,
            "trace_metadata": {},
            "provider_id": provider_id,
            "model_name": model_name,
            "evaluation": None,
            "selected_model": "",
            "routing_confidence": 0.0,
            "routing_reason": "default",
            # selected_tools 由 engine 动态选择，不传则 default_factory=list 自动给 []
        }

        config = self._get_config(conversation_id)
        result = await self._graph.ainvoke(initial_state, config=config)

        elapsed = int((time.time() - t0) * 1000)

        # 工具使用统计
        for tool_name in result.get("tools_used", []):
            self._record_tool_usage(tool_name, success=True, duration_ms=elapsed)

        # 追踪
        from app.agent.tracing import trace_agent_run, AgentTrace
        trace_agent_run(AgentTrace(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=messages[-1].get("content", "") if messages else "",
            final_answer=result.get("final_answer", "") or "",
            intent_hit=result.get("intent", {}).get("intent_name") if result.get("intent") else None,
            tools_used=result.get("tools_used", []),
            iterations=result.get("iterations", 0),
            total_duration_ms=elapsed,
            prompt_tokens=result.get("prompt_tokens", 0),
            completion_tokens=result.get("completion_tokens", 0),
        ))

        return {
            "content": result.get("final_answer") or "",
            "tools_used": result.get("tools_used", []),
            "iterations": result.get("iterations", 0),
            "needs_approval": result.get("needs_approval", False),
            "pending_tool_call": result.get("pending_tool_call"),
            "intent": result.get("intent"),
            "evaluation": result.get("evaluation"),
            "duration_ms": elapsed,
        }

    async def resume(
        self,
        conversation_id: int,
        approved: bool,
        tool_name: str = "",
        tool_args: Optional[dict] = None,
        user_response: str = "",
    ) -> Dict[str, Any]:
        """
        resume 端点：恢复被 interrupt 暂停的 Agent 执行。

        Args:
            conversation_id: 会话 ID
            approved: 是否批准执行
            tool_name: 工具名（可选，用于日志）
            tool_args: 工具参数（可选，edit 场景使用修改后的参数）
            user_response: 用户回复（可选，respond 场景）
        """
        if not self.is_ready:
            return {"error": "Agent 引擎未初始化"}

        from langgraph.types import Command

        t0 = time.time()
        config = self._get_config(conversation_id)

        resume_data = {
            "approved": approved,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "user_response": user_response,
        }

        try:
            result = await self._graph.ainvoke(
                Command(resume=resume_data),
                config=config,
            )
            elapsed = int((time.time() - t0) * 1000)

            return {
                "content": result.get("final_answer") or "",
                "tools_used": result.get("tools_used", []),
                "iterations": result.get("iterations", 0),
                "duration_ms": elapsed,
            }
        except Exception as e:
            logger.error(f"Agent resume 失败: {e}", exc_info=True)
            return {"error": str(e)}

    async def resume_stream(
        self,
        conversation_id: int,
        approved: bool,
        tool_name: str = "",
        tool_args: Optional[dict] = None,
        user_response: str = "",
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式 resume — LangGraph v3 Event Streaming"""
        if not self.is_ready:
            yield {"type": "error", "message": "Agent 引擎未初始化"}
            return

        from langgraph.types import Command

        t0 = time.time()
        config = self._get_config(conversation_id)

        resume_data = {
            "approved": approved,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "user_response": user_response,
        }

        tools_used = []

        try:
            stream = self._graph.astream_events(
                Command(resume=resume_data),
                config=config,
                version="v3",
            )

            _final_answer = None
            _got_llm_tokens = False

            async for event in stream:
                method = event.get("method", "")
                params = event.get("params", {})
                data = params.get("data", {}) if isinstance(params, dict) else {}

                if method == "messages":
                    if not isinstance(data, (list, tuple)) or len(data) < 2:
                        continue
                    msg_chunk, metadata = data[0], data[1] if len(data) > 1 else {}
                    if isinstance(data, dict) and data.get("event") == "content-block-delta":
                        block = (data.get("delta") or {})
                        if block.get("type") == "text-delta":
                            token_text = block.get("text", "")
                            if token_text:
                                _got_llm_tokens = True
                                yield {"type": "token", "content": token_text}
                    elif hasattr(msg_chunk, "content") and msg_chunk.content and hasattr(msg_chunk, "type"):
                        if getattr(msg_chunk, "type", "") == "AIMessageChunk":
                            _got_llm_tokens = True
                            token_text = msg_chunk.content if isinstance(msg_chunk.content, str) else _content_blocks_to_str(msg_chunk.content)
                            yield {"type": "token", "content": token_text}

                elif method == "tools":
                    event_type = event.get("event", "")
                    tn = data.get("name", "") if isinstance(data, dict) else ""
                    if event_type == "on_tool_start" and tn:
                        tools_used.append(tn)
                        yield {"type": "tool_start", "tool": tn, "args": data.get("input", {}) if isinstance(data, dict) else {}}
                    elif event_type in ("on_tool_end", "on_tool_error"):
                        output_str = str(data.get("output", "")) if isinstance(data, dict) else ""
                        is_err = event_type == "on_tool_error" or '"success": false' in output_str.lower() or '"error"' in output_str.lower()
                        if is_err:
                            yield {"type": "tool_error", "tool": tn, "output_preview": output_str[:200]}
                        else:
                            yield {"type": "tool_end", "tool": tn, "output_preview": output_str[:200]}

                elif method == "custom":
                    if isinstance(data, dict):
                        yield {"type": "progress", **data}

                elif method == "updates":
                    if isinstance(data, dict):
                        for node_output in data.values():
                            if isinstance(node_output, dict) and node_output.get("final_answer"):
                                _final_answer = node_output["final_answer"]

            # 缓存答案 fallback
            if not _got_llm_tokens and not _final_answer:
                try:
                    if self._graph and hasattr(self._graph, 'get_state'):
                        state_snapshot = self._graph.get_state(config)
                        if state_snapshot and state_snapshot.values:
                            _final_answer = state_snapshot.values.get("final_answer") or ""
                            if not _final_answer:
                                for msg in reversed(state_snapshot.values.get("messages", [])):
                                    content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
                                    if content:
                                        _final_answer = content
                                        break
                except Exception:
                    pass

            if _final_answer and not _got_llm_tokens:
                yield {"type": "token", "content": _final_answer}

            elapsed = int((time.time() - t0) * 1000)
            yield {
                "type": "done",
                "tools_used": tools_used,
                "duration_ms": elapsed,
            }

        except Exception as e:
            logger.error(f"Agent resume_stream 失败: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}

    async def chat_stream(
        self,
        conversation_id: int,
        user_id: int,
        messages: list,
        provider_id: int = 0,
        model_name: str = "",
        reasoning_depth: str = "balanced",
        team_mode: str = "off",
        team_id: int | None = None,
        skill_id: int | None = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Agent 流式对话（v4.3 — 新增专家团/技能手动指定）"""
        if not self.is_ready:
            success = await self._lazy_init(provider_id, model_name)
            if not success:
                yield {"type": "error", "message": "Agent 引擎初始化失败"}
                return

        t0 = time.time()
        tools_used = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        # ── 手动指定技能：直接执行，不走 Agent 流程 ──
        if skill_id:
            try:
                from app.core.database import AsyncSessionLocal
                from app.services.skill_service import SkillService
                from app.agent.skill_executor import skill_executor

                async def _skill_progress(event: dict):
                    """技能进度回调 → 转为 SSE progress 事件"""
                    yield_event = {"type": "progress", **event}
                    # 通过外层 yield 返回（闭包引用外层 async generator）
                    _skill_progress_events.append(yield_event)

                _skill_progress_events: list = []

                async with AsyncSessionLocal() as skill_db:
                    svc = SkillService()
                    skill = await svc.get_skill_by_id(skill_db, skill_id)
                    if skill:
                        import asyncio

                        async def _run_skill():
                            return await skill_executor.execute(
                                db=skill_db,
                                skill_name=skill.name,
                                user_message=messages[-1].get("content", ""),
                                messages=messages,
                                provider_id=provider_id,
                                model_name=model_name,
                                on_progress=_skill_progress,
                            )

                        # 并行：技能执行 + 进度事件 yield
                        skill_task = asyncio.create_task(_run_skill())
                        while not skill_task.done():
                            while _skill_progress_events:
                                yield _skill_progress_events.pop(0)
                            await asyncio.sleep(0.05)
                        # 收尾：剩余进度事件
                        while _skill_progress_events:
                            yield _skill_progress_events.pop(0)

                        answer = skill_task.result()
                        if answer:
                            yield {"type": "token", "content": answer}
                            elapsed = int((time.time() - t0) * 1000)
                            yield {"type": "done", "tools_used": [], "duration_ms": elapsed, "prompt_tokens": 0, "completion_tokens": 0}
                            return
                    yield {"type": "error", "message": f"技能 ID {skill_id} 不存在"}
            except Exception as e:
                logger.error(f"[chat_stream] 技能执行失败: {e}", exc_info=True)
                yield {"type": "error", "message": f"技能执行失败: {e}"}
            return

        # ── 专家团 auto 模式：先尝试匹配意图 → 命中则执行专家团 ──
        if team_mode == "auto":
            user_msg = messages[-1].get("content", "") if messages else ""
            matched_team = await self._try_match_expert_team(user_msg)
            if matched_team:
                logger.info(f"[chat_stream] auto 模式命中专家团: {matched_team['team_name']} (id={matched_team['team_id']})")
                yield {"type": "progress", "step": "expert_team", "status": "matched",
                       "message": f"自动匹配到专家团「{matched_team['team_name']}」"}
                async for event in self._execute_expert_team_stream(matched_team["team_id"], user_msg):
                    yield event
                return
            logger.info("[chat_stream] auto 模式未命中专家团，走常规 Agent")

        try:
            initial_state = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "messages": messages,
                "context": "",
                "system_prompt": "",
                "tool_calls": [],
                "tools_used": [],
                "final_answer": None,
                "iterations": 0,
                "needs_approval": False,
                "pending_tool_call": None,
                "intent": None,
                "skill_answer": None,
                "error": None,
                "trace_metadata": {},
                "provider_id": provider_id,
                "model_name": model_name,
                "evaluation": None,
                "reasoning_depth": reasoning_depth,
                "selected_model": "",
                "routing_confidence": 0.0,
                "routing_reason": "default",
                # selected_tools 由 engine 动态选择，不传则 default_factory=list 自动给 []
            }

            config = self._get_config(conversation_id)

            # ── 快速路径：闲聊用 ainvoke，避免流式挂起 ──
            from app.agent.intent_router import _detect_chitchat
            user_msg = messages[-1].get("content", "") if messages else ""
            if _detect_chitchat(user_msg):
                logger.info(f"[chat_stream] 闲聊快速路径: ainvoke")
                result = await self._graph.ainvoke(initial_state, config=config)
                answer = result.get("final_answer") or ""
                if not answer:
                    for msg in reversed(result.get("messages", [])):
                        content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
                        if content:
                            answer = content
                            break
                if answer:
                    yield {"type": "token", "content": answer}
                elapsed = int((time.time() - t0) * 1000)
                yield {"type": "done", "tools_used": [], "duration_ms": elapsed, "prompt_tokens": 0, "completion_tokens": 0}
                return

            # [P0] LangGraph v3 Event Streaming — 官方推荐的 typed projection API
            # 文档: https://docs.langchain.com/oss/python/langgraph/event-streaming
            # v3 核心优势: 每个 projection（messages/values/output）独立消费，天然去重
            stream = await self._graph.astream_events(
                initial_state,
                config=config,
                version="v3",
            )

            _final_answer = None
            _got_llm_tokens = False

            async for event in stream:
                method = event.get("method", "")
                params = event.get("params", {})
                data = params.get("data", {}) if isinstance(params, dict) else {}

                # ── messages 通道: LLM token 流式输出 ──
                if method == "messages":
                    if not isinstance(data, (list, tuple)) or len(data) < 2:
                        continue
                    msg_chunk, metadata = data[0], data[1] if len(data) > 1 else {}
                    node_name = metadata.get("langgraph_node", "") if isinstance(metadata, dict) else ""

                    # v3: data = (payload, metadata); payload 是 dict（protocol event）或 BaseMessage
                    # ── content-block-delta: 流式 token（文本生成过程中的增量） ──
                    if isinstance(msg_chunk, dict) and msg_chunk.get("event") == "content-block-delta":
                        block = (msg_chunk.get("delta") or {})
                        if block.get("type") == "text-delta":
                            token_text = block.get("text", "")
                            if token_text:
                                _got_llm_tokens = True
                                yield {"type": "token", "content": token_text}
                    # ── content-block-start: reasoning / thinking 内容 ──
                    elif isinstance(msg_chunk, dict) and msg_chunk.get("event") == "content-block-start":
                        block = msg_chunk.get("content_block", {})
                        if isinstance(block, dict) and block.get("type") == "thinking":
                            thinking_text = block.get("thinking", "")
                            if thinking_text:
                                yield {"type": "token", "content": thinking_text}
                    # ── reasoning-delta: reasoning 流式增量 ──
                    elif isinstance(msg_chunk, dict) and msg_chunk.get("event") == "reasoning-delta":
                        reasoning_text = msg_chunk.get("delta", {}).get("reasoning", "") if isinstance(msg_chunk.get("delta"), dict) else ""
                        if reasoning_text:
                            yield {"type": "token", "content": reasoning_text}
                    # 兼容 v2: AIMessageChunk（LangChain 模型返回的完整 chunk）
                    elif hasattr(msg_chunk, "content") and msg_chunk.content and hasattr(msg_chunk, "type"):
                        if getattr(msg_chunk, "type", "") == "AIMessageChunk":
                            _got_llm_tokens = True
                            token_text = msg_chunk.content if isinstance(msg_chunk.content, str) else _content_blocks_to_str(msg_chunk.content)
                            yield {"type": "token", "content": token_text}

                    # 提取 usage
                    if isinstance(msg_chunk, dict) and msg_chunk.get("event") == "message-finish":
                        usage = msg_chunk.get("usage") or {}
                        pt = usage.get("input_tokens", 0) or 0
                        ct = usage.get("output_tokens", 0) or 0
                        if pt or ct:
                            total_prompt_tokens += pt
                            total_completion_tokens += ct
                            yield {"type": "cost_update", "prompt_tokens": total_prompt_tokens, "completion_tokens": total_completion_tokens}
                    elif hasattr(msg_chunk, "usage_metadata") and msg_chunk.usage_metadata:
                        usage = msg_chunk.usage_metadata
                        pt = getattr(usage, "input_tokens", 0) or 0
                        ct = getattr(usage, "output_tokens", 0) or 0
                        if pt or ct:
                            total_prompt_tokens += pt
                            total_completion_tokens += ct
                            yield {"type": "cost_update", "prompt_tokens": total_prompt_tokens, "completion_tokens": total_completion_tokens}

                # ── tools 通道: 工具调用事件（v3: tool-started / tool-output-delta / tool-finished / tool-error） ──
                elif method == "tools":
                    event_type = data.get("event", "") if isinstance(data, dict) else ""
                    tool_name = data.get("tool_name", "") if isinstance(data, dict) else ""

                    if event_type == "tool-started":
                        if tool_name:
                            tools_used.append(tool_name)
                            yield {"type": "tool_start", "tool": tool_name, "args": data.get("input", {}) if isinstance(data, dict) else {}}

                    elif event_type in ("tool-finished", "tool-error"):
                        output_str = str(data.get("output", "")) if isinstance(data, dict) else ""
                        is_error = event_type == "tool-error"
                        if is_error:
                            yield {"type": "tool_error", "tool": tool_name, "output_preview": output_str[:200]}
                        else:
                            yield {"type": "tool_end", "tool": tool_name, "output_preview": output_str[:200]}

                # ── custom 通道: get_stream_writer() 发射的进展事件 ──
                elif method == "custom":
                    if isinstance(data, dict):
                        yield {"type": "progress", **data}

                # ── updates 通道: 节点状态更新 ──
                elif method == "updates":
                    if isinstance(data, dict):
                        for node_output in data.values():
                            if isinstance(node_output, dict) and node_output.get("final_answer"):
                                _final_answer = node_output["final_answer"]

            # 获取最终状态（stream.output 等价于 get_state）
            final_state = None
            try:
                if self._graph and hasattr(self._graph, 'get_state'):
                    state_snapshot = self._graph.get_state(config)
                    if state_snapshot and state_snapshot.values:
                        final_state = state_snapshot.values
            except Exception:
                pass

            # interrupt 检测（审批暂停）
            try:
                if self._graph and hasattr(self._graph, 'get_state'):
                    state_snapshot = self._graph.get_state(config)
                    if state_snapshot and hasattr(state_snapshot, 'next') and state_snapshot.next:
                        for pending_node in state_snapshot.next:
                            if pending_node == "approval_node":
                                pending = (final_state or {}).get("pending_tool_call")
                                if pending:
                                    yield {
                                        "type": "approval_required",
                                        "tool": pending.get("name", ""),
                                        "args": pending.get("args", {}),
                                        "message": pending.get("message", "需要用户确认"),
                                    }
                                    return
            except Exception:
                pass

            # 缓存答案 fallback（chitchat/语义缓存命中，LLM 未被调用）
            logger.info(f"[chat_stream] 流结束: final_answer={'set' if _final_answer else 'None'} llm_tokens={_got_llm_tokens}")
            if not _final_answer and final_state:
                _final_answer = final_state.get("final_answer") or ""
                if not _final_answer:
                    for msg in reversed(final_state.get("messages", [])):
                        content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
                        if content:
                            _final_answer = content
                            break
                if _final_answer:
                    yield {"type": "token", "content": _final_answer}

            # 意图引用
            if final_state:
                intent = final_state.get("intent")
                if intent:
                    yield {"type": "intent_hit", "intent": intent.get("intent_name", ""), "score": intent.get("score", 0)}

            elapsed = int((time.time() - t0) * 1000)

            # 追踪
            try:
                from app.agent.tracing import trace_agent_run, AgentTrace
                trace_agent_run(AgentTrace(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    user_message=messages[-1].get("content", "") if messages else "",
                    tools_used=tools_used,
                    total_duration_ms=elapsed,
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                ))
            except Exception:
                pass

            yield {
                "type": "done",
                "tools_used": tools_used,
                "duration_ms": elapsed,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
            }

        except Exception as e:
            logger.error(f"Agent 流式对话失败: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}

    def _record_tool_usage(self, tool_name: str, success: bool, duration_ms: int):
        """记录工具使用统计"""
        if tool_name not in self._tool_stats:
            self._tool_stats[tool_name] = {"calls": 0, "success": 0, "fail": 0, "total_ms": 0}
        stats = self._tool_stats[tool_name]
        stats["calls"] += 1
        if success:
            stats["success"] += 1
        else:
            stats["fail"] += 1
        stats["total_ms"] += duration_ms

    def get_tool_stats(self) -> Dict[str, Dict]:
        """获取工具使用统计"""
        return dict(self._tool_stats)

    # ── P2: Time Travel（状态历史查询）────────────────────

    async def get_state_history(self, conversation_id: int, limit: int = 10) -> list:
        """获取图状态历史（Time Travel）。

        返回最近 N 个 checkpoint 快照，用于调试和状态回溯。
        """
        if not self.is_ready or not self._graph:
            return []
        config = self._get_config(conversation_id)
        try:
            history = []
            async for state_snapshot in self._graph.aget_state_history(config, limit=limit):
                history.append({
                    "checkpoint_id": getattr(state_snapshot, 'config', {}).get('configurable', {}).get('checkpoint_id', ''),
                    "values": {
                        k: v for k, v in (state_snapshot.values or {}).items()
                        if k in ('final_answer', 'intent', 'tools_used', 'evaluation', 'error', 'iterations')
                    },
                    "next": list(state_snapshot.next) if hasattr(state_snapshot, 'next') and state_snapshot.next else [],
                    "created_at": str(getattr(state_snapshot, 'created_at', '')),
                })
            return history
        except Exception as e:
            logger.warning(f"[time_travel] 状态历史查询失败: {e}")
            return []

    async def fork_state(self, conversation_id: int, checkpoint_id: str) -> bool:
        """从指定 checkpoint 分叉状态（Time Travel fork）。

        将图状态回滚到指定 checkpoint，后续操作从该点继续。
        """
        if not self.is_ready or not self._graph:
            return False
        config = self._get_config(conversation_id)
        config["configurable"] = config.get("configurable", {})
        config["configurable"]["checkpoint_id"] = checkpoint_id
        try:
            state_snapshot = await self._graph.aget_state(config)
            if state_snapshot and state_snapshot.values:
                logger.info(f"[time_travel] 状态已回滚到 checkpoint: {checkpoint_id}")
                return True
            return False
        except Exception as e:
            logger.warning(f"[time_travel] 状态回滚失败: {e}")
            return False

    # ── 专家团自动匹配 ────────────────────────────────────

    async def _try_match_expert_team(self, user_msg: str) -> dict | None:
        """尝试匹配专家团 — 基于意图路由 + 专家团关键词/描述匹配

        匹配策略（优先级从高到低）:
          1. 意图表中 target_module = "expert_team:{team_id}" 的精确匹配
          2. 专家团 description 与用户消息的语义相似度（简单关键词匹配）

        Returns:
            {"team_id": int, "team_name": str} 或 None
        """
        if not user_msg or not user_msg.strip():
            return None

        try:
            from app.core.database import AsyncSessionLocal
            from app.services.expert_team_service import ExpertTeamService

            async with AsyncSessionLocal() as db:
                service = ExpertTeamService()
                teams, _ = await service.list_teams(db, page=1, page_size=100, enabled=1)
                if not teams:
                    return None

                # 简单关键词匹配（后续可升级为向量相似度）
                user_lower = user_msg.lower()
                best_match = None
                best_score = 0

                for team in teams:
                    score = 0
                    # 检查团队名称
                    if team.teamName and team.teamName.lower() in user_lower:
                        score += 3
                    # 检查描述关键词
                    if team.description:
                        desc_words = team.description.lower().split()
                        for word in desc_words:
                            if len(word) >= 2 and word in user_lower:
                                score += 1
                    # 检查分类
                    if team.category and team.category.lower() in user_lower:
                        score += 2

                    if score > best_score:
                        best_score = score
                        best_match = team

                # 阈值：至少要命中 2 分才认为是有效匹配
                if best_match and best_score >= 2:
                    return {"team_id": best_match.id, "team_name": best_match.teamName}

        except Exception as e:
            logger.warning(f"[_try_match_expert_team] 匹配失败: {e}")

        return None

    async def _execute_expert_team_stream(self, team_id: int, user_msg: str) -> AsyncIterator[Dict[str, Any]]:
        """执行专家团并以流式事件返回（实时进度）"""
        import asyncio
        from app.services.expert_team_service import ExpertTeamService
        from app.schemas.expert_team import ExpertTeamExecuteRequest

        t0 = time.time()
        _progress_events: list = []

        async def _on_progress(event: dict):
            """专家团进度回调 → 收集事件供外层 yield"""
            event_type = event.get("type", "")
            NL = "\n"
            # 构建 progress 事件
            if event_type == "expert_start":
                name = event.get("expertName", "")
                role = event.get("expertRole", "")
                _progress_events.append({"type": "progress", "step": f"expert_{name}", "status": "executing", "message": f"{name}({role}) 正在分析..."})
                # 同时生成 content token
                avatar = event.get("avatar", "")
                subtask = event.get("subtask", "")
                prefix = f"{avatar} " if avatar else ""
                _progress_events.append({"type": "token", "content": f"**{prefix}{name}** ({role}){NL}{subtask}{NL}{NL}"})
            elif event_type == "expert_done":
                name = event.get("expertName", "")
                role = event.get("expertRole", "")
                duration = event.get("durationMs", 0)
                content = event.get("content", "")
                _progress_events.append({"type": "progress", "step": f"expert_{name}", "status": "done", "message": f"{name}({role}) 分析完成", "elapsedMs": duration})
                avatar = event.get("avatar", "")
                prefix = f"{avatar} " if avatar else ""
                _progress_events.append({"type": "token", "content": f"**{prefix}{name}** ({role}) · {duration}ms{NL}"})
                _progress_events.append({"type": "token", "content": content + NL + NL})
            elif event_type == "pm_done":
                name = event.get("expertName", "PM")
                content = event.get("content", "")
                _progress_events.append({"type": "progress", "step": "pm_plan", "status": "done", "message": f"{name} 任务规划完成"})
                _progress_events.append({"type": "token", "content": f"**◆ {name}** 分析完成:{NL}"})
                _progress_events.append({"type": "token", "content": content + NL + NL})
            elif event_type == "pm_eval":
                content = event.get("content", "")
                _progress_events.append({"type": "progress", "step": "pm_eval", "status": "done", "message": "PM 评估完成"})
                _progress_events.append({"type": "token", "content": f"**◆ PM 评估:**{NL}"})
                _progress_events.append({"type": "token", "content": content + NL + NL})
            elif event_type == "pm_report":
                content = event.get("content", "")
                _progress_events.append({"type": "progress", "step": "expert_team", "status": "done", "message": "专家团执行完成"})
                _progress_events.append({"type": "token", "content": f"---{NL}**◆ 最终报告:**{NL}{NL}"})
                _progress_events.append({"type": "token", "content": content})

        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                service = ExpertTeamService()
                request = ExpertTeamExecuteRequest(input_text=user_msg)

                async def _run_team():
                    return await service.execute_team(db, team_id, request, on_progress=_on_progress)

                # 并行：专家团执行 + 进度事件 yield
                team_task = asyncio.create_task(_run_team())
                while not team_task.done():
                    while _progress_events:
                        yield _progress_events.pop(0)
                    await asyncio.sleep(0.05)
                # 收尾：剩余进度事件
                while _progress_events:
                    yield _progress_events.pop(0)

                result = team_task.result()
                elapsed = int((time.time() - t0) * 1000)
                yield {"type": "done", "tools_used": [], "duration_ms": elapsed,
                       "prompt_tokens": 0, "completion_tokens": 0}

        except Exception as e:
            logger.error(f"专家团流式执行失败: {e}", exc_info=True)
            yield {"type": "error", "message": f"专家团执行失败: {e}"}

    async def _lazy_init(self, provider_id: int, model_name: str) -> bool:
        """懒初始化 — 双重检查锁 + provider 变更检测

        当用户切换供应商/模型时，需要重建 graph。
        """
        # 快速路径：已初始化且 provider 匹配
        if self._initialized and self._graph is not None:
            if self._provider_id == provider_id and self._model_name == model_name:
                return True
            # provider 变更，需要重新初始化
            logger.info(f"[lazy_init] provider 变更: ({self._provider_id},{self._model_name}) → ({provider_id},{model_name})")

        async with self._init_lock:
            # 双重检查（锁内再查一次）
            if self._initialized and self._graph is not None:
                if self._provider_id == provider_id and self._model_name == model_name:
                    return True

            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                return await self.initialize(db, provider_id=provider_id, model_name=model_name)

    def reset(self):
        self._graph = None
        self._provider_id = None
        self._model_name = ""
        self._initialized = False
        logger.info("Agent 引擎已重置")


agent_service = AgentService()
