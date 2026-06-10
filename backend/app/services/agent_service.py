"""Agent 业务服务 — v4.3 完整版

v4.3 变更:
  1. [P0] 流式对话改用 astream + stream_mode=["messages","updates"]，替代已废弃的 astream_events v3
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
        self._provider_id: Optional[int] = None
        self._model_name: str = ""
        self._initialized = False
        self._enable_interrupt = False
        self._tool_stats: Dict[str, Dict] = {}  # 工具使用统计
        self._init_lock = asyncio.Lock()  # [P1] 防止并发初始化竞态

    @property
    def is_ready(self) -> bool:
        return self._graph is not None

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

            # ── v5.1: Tier Selector（模型路由）─────────────
            from app.llm.tier_selector import TierSelector
            tier_selector = TierSelector()
            tier_selector.register("c0", llm, model_name=f"{model_name}(c0)")
            tier_selector.register("c1", llm, model_name=f"{model_name}(c1)")
            tier_selector.register("c2", llm, model_name=f"{model_name}(c2)")
            # 后续可替换为不同模型:
            # cheap_llm = await llm_service.get_chat_llm(db, provider_id=..., model_name="qwen3:7b")
            # tier_selector.register("c0", cheap_llm, model_name="qwen3:7b")

            memory_manager = memory_service.memory_manager
            intent_router = intent_service.intent_router

            # RAG pipeline 注入
            rag_pipeline = None
            try:
                from app.agent.rag_pipeline import RAGPipeline
                from app.core.config import get_settings
                _settings = get_settings()
                qdrant_url = f"http://{_settings.QDRANT_HOST}:{_settings.QDRANT_PORT}"
                rag_pipeline = RAGPipeline(
                    qdrant_url=qdrant_url,
                    embedding_model=None,  # 由 RAGPipeline 内部初始化
                )
                logger.info(f"RAG pipeline 已注入 ContextEngine (qdrant={qdrant_url})")
            except Exception as e:
                logger.warning(f"RAG pipeline 初始化跳过: {e}")

            context_engine = ContextEngine(
                memory_manager=memory_manager,
                rag_pipeline=rag_pipeline,
                tool_registry=tool_registry,
            )

            self._enable_interrupt = enable_interrupt
            self._graph = build_agent_graph(
                llm=llm,
                tool_registry=tool_registry,
                context_engine=context_engine,
                memory_manager=memory_manager,
                intent_router=intent_router,
                skill_executor=skill_executor,
                rag_pipeline=rag_pipeline,
                tier_selector=tier_selector,
                enable_interrupt=enable_interrupt,
            )
            self._provider_id = provider_id
            self._model_name = model_name
            self._initialized = True

            logger.info(f"Agent 引擎 v5.1 初始化完成 (provider={provider_id}, model={model_name}, SquillaRouter+B+C动态工具, interrupt={enable_interrupt})")
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
            "model_tier": "c1",
            "model_tier_confidence": 0.0,
            "model_tier_reason": "default",
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
        """流式 resume — 按 LangGraph 官方规范使用 astream(Command(resume=...))

        官方文档: https://docs.langchain.com/oss/python/langgraph/interrupts
        推荐模式: graph.astream(Command(resume=...), stream_mode=["messages","updates"], version="v2")
        """
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
            stream = self._graph.astream(
                Command(resume=resume_data),
                config=config,
                stream_mode=["messages", "updates", "custom"],
                version="v2",
            )

            _final_answer = None
            _got_llm_tokens = False

            async for chunk in stream:
                chunk_type = chunk.get("type", "")
                chunk_data = chunk.get("data", None)

                if chunk_type == "messages":
                    msg_chunk, metadata = chunk_data
                    if hasattr(msg_chunk, "content") and msg_chunk.content:
                        _got_llm_tokens = True
                        token = msg_chunk.content if isinstance(msg_chunk.content, str) else _content_blocks_to_str(msg_chunk.content)
                        yield {"type": "token", "content": token}

                elif chunk_type == "updates":
                    if isinstance(chunk_data, dict):
                        for node_name, node_output in chunk_data.items():
                            if not isinstance(node_output, dict):
                                continue
                            if node_output.get("final_answer"):
                                _final_answer = node_output["final_answer"]
                            if node_name == "tool_executor":
                                for msg in node_output.get("messages", []):
                                    if isinstance(msg, dict) and msg.get("role") == "tool":
                                        tn = msg.get("name", "unknown")
                                        yield {"type": "tool_end", "tool": tn, "output_preview": str(msg.get("content", ""))[:200]}
                            if node_name == "llm_call" and node_output.get("tool_calls"):
                                for tc in node_output["tool_calls"]:
                                    tn = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                                    ta = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                                    tools_used.append(tn)
                                    yield {"type": "tool_start", "tool": tn, "args": ta if isinstance(ta, dict) else {}}

                elif chunk_type == "custom":
                    # 自定义进展事件 — 从 get_stream_writer() 发射
                    if isinstance(chunk_data, dict):
                        yield {"type": "progress", **chunk_data}

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
    ) -> AsyncIterator[Dict[str, Any]]:
        """Agent 流式对话（v4.1 — 新增审批/工具进度/上下文引用/成本事件）"""
        if not self.is_ready:
            success = await self._lazy_init(provider_id, model_name)
            if not success:
                yield {"type": "error", "message": "Agent 引擎初始化失败"}
                return

        t0 = time.time()
        tools_used = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

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
                "model_tier": "c1",
                "model_tier_confidence": 0.0,
                "model_tier_reason": "default",
                # selected_tools 由 engine 动态选择，不传则 default_factory=list 自动给 []
            }

            config = self._get_config(conversation_id)

            # ── 快速路径：闲聊/缓存命中用 ainvoke，避免 v3 流式挂起 ──
            # LangGraph v1.x 的 MemorySaver + astream_events 在图快速完成时
            # （如闲聊直接到 END）可能流不关闭。用 ainvoke 绕过。
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

            # [P0] 使用 LangGraph 原生 astream（v2 stream_mode）
            # 旧代码用 astream_events(version="v3") 但用 v2 方式迭代 —— v3 API 已改为
            # typed projections（stream.messages），直接迭代收不到任何事件。
            # 改用 astream + stream_mode=["messages", "updates", "custom"]，官方推荐方案。
            stream = self._graph.astream(
                initial_state,
                config=config,
                stream_mode=["messages", "updates", "custom"],
                version="v2",
            )

            _final_answer = None
            _got_llm_tokens = False

            async for chunk in stream:
                chunk_type = chunk.get("type", "")
                chunk_data = chunk.get("data", None)

                if chunk_type == "messages":
                    # LLM token 流式输出 — (message_chunk, metadata) 元组
                    msg_chunk, metadata = chunk_data
                    if hasattr(msg_chunk, "content") and msg_chunk.content:
                        _got_llm_tokens = True
                        token = msg_chunk.content if isinstance(msg_chunk.content, str) else _content_blocks_to_str(msg_chunk.content)
                        yield {"type": "token", "content": token}
                    # 提取 usage
                    if hasattr(msg_chunk, "usage_metadata") and msg_chunk.usage_metadata:
                        usage = msg_chunk.usage_metadata
                        pt = getattr(usage, "input_tokens", 0) or 0
                        ct = getattr(usage, "output_tokens", 0) or 0
                        if pt or ct:
                            total_prompt_tokens += pt
                            total_completion_tokens += ct
                            yield {"type": "cost_update", "prompt_tokens": total_prompt_tokens, "completion_tokens": total_completion_tokens}

                elif chunk_type == "updates":
                    # 节点状态更新 — {node_name: state_delta} 或 {node_name: state_delta, ...}
                    if isinstance(chunk_data, dict):
                        for node_name, node_output in chunk_data.items():
                            if not isinstance(node_output, dict):
                                continue
                            # 捕获 final_answer
                            if node_output.get("final_answer"):
                                _final_answer = node_output["final_answer"]
                            # 工具执行事件
                            if node_name == "tool_executor":
                                # 工具结果在 messages 里
                                for msg in node_output.get("messages", []):
                                    if isinstance(msg, dict) and msg.get("role") == "tool":
                                        tool_name = msg.get("name", "unknown")
                                        output_preview = str(msg.get("content", ""))[:200]
                                        yield {"type": "tool_end", "tool": tool_name, "output_preview": output_preview}
                            # 工具调用事件（从 llm_call 的 tool_calls 字段）
                            if node_name == "llm_call" and node_output.get("tool_calls"):
                                for tc in node_output["tool_calls"]:
                                    tool_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                                    tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                                    tools_used.append(tool_name)
                                    yield {"type": "tool_start", "tool": tool_name, "args": tool_args if isinstance(tool_args, dict) else {}}

                elif chunk_type == "custom":
                    # 自定义进展事件 — 从 get_stream_writer() 发射
                    if isinstance(chunk_data, dict):
                        yield {"type": "progress", **chunk_data}

            # 检查 interrupt（审批暂停）— 通过 get_state 检查
            try:
                if self._graph and hasattr(self._graph, 'get_state'):
                    state_snapshot = self._graph.get_state(config)
                    if state_snapshot and hasattr(state_snapshot, 'next') and state_snapshot.next:
                        # 有 pending node = interrupt 状态
                        for pending_node in state_snapshot.next:
                            if pending_node == "approval_node":
                                # 从 state 读取 pending_tool_call
                                values = state_snapshot.values or {}
                                pending = values.get("pending_tool_call")
                                if pending:
                                    yield {
                                        "type": "approval_required",
                                        "tool": pending.get("name", ""),
                                        "args": pending.get("args", {}),
                                        "message": pending.get("message", "需要用户确认"),
                                    }
                                    return  # 审批模式下不发 done
            except Exception:
                pass

            # 发送缓存答案（chitchat/语义缓存命中，LLM 未被调用）
            logger.info(f"[chat_stream] 流结束: final_answer={'set' if _final_answer else 'None'} llm_tokens={_got_llm_tokens}")
            if not _final_answer:
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
                except Exception as e:
                    logger.warning(f"[chat_stream] 读取 graph state 失败: {e}")

                if _final_answer:
                    yield {"type": "token", "content": _final_answer}
                else:
                    logger.warning("[chat_stream] 无法提取 final_answer")

            # 发送上下文引用
            try:
                if self._graph and hasattr(self._graph, 'get_state'):
                    state = self._graph.get_state(config)
                    if state and state.values:
                        intent = state.values.get("intent")
                        if intent:
                            yield {"type": "intent_hit", "intent": intent.get("intent_name", ""), "score": intent.get("score", 0)}
            except Exception:
                pass

            elapsed = int((time.time() - t0) * 1000)

            # 追踪（流式路径）
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
