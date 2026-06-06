"""Agent 业务服务 — v4.2 完整版

v4.2 变更:
  1. [P0] 流式对话升级 stream_events v3，支持 interrupt/resume 审批事件
  2. [P1] 初始化加 asyncio.Lock 防竞态
  3. [P2] LLM 缓存加 TTL 过期机制
"""
import asyncio
import time
import uuid
from typing import Optional, AsyncIterator, Dict, Any

from app.core.logging import get_logger

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
        """初始化 Agent 引擎"""
        from app.agent.llm_service import llm_service
        from app.agent.tool_registry import tool_registry, register_builtin_tools
        from app.agent.engine import build_agent_graph
        from app.agent.context_engine import ContextEngine
        from app.services.memory_service import memory_service
        from app.services.intent_service import intent_service

        try:
            register_builtin_tools()
            await tool_registry.load_from_db(db)

            lc_tools = tool_registry.get_langchain_tools(tool_names)
            llm = await llm_service.get_chat_llm(
                db, provider_id=provider_id, model_name=model_name, bind_tools=lc_tools,
            )

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
                skill_executor=None,
                rag_pipeline=rag_pipeline,
                enable_interrupt=enable_interrupt,
            )
            self._provider_id = provider_id
            self._model_name = model_name
            self._initialized = True

            logger.info(f"Agent 引擎 v3.0 初始化完成 (provider={provider_id}, model={model_name}, tools={len(lc_tools)}, interrupt={enable_interrupt})")
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
            }

            config = self._get_config(conversation_id)

            # [P0] 升级到 v3 以支持 interrupt/resume 事件
            # v3 返回协程，需 await 获取流对象
            stream = await self._graph.astream_events(initial_state, config=config, version="v3")

            async for event in stream:
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield {"type": "token", "content": chunk.content}

                elif kind == "on_chat_model_end":
                    # 提取 token 使用量
                    output = event.get("data", {}).get("output", None)
                    if output:
                        usage = getattr(output, "usage_metadata", None) or getattr(output, "usage", None)
                        if usage:
                            pt = getattr(usage, "input_tokens", 0) or (usage.get("input_tokens", 0) if isinstance(usage, dict) else 0)
                            ct = getattr(usage, "output_tokens", 0) or (usage.get("output_tokens", 0) if isinstance(usage, dict) else 0)
                            total_prompt_tokens += pt
                            total_completion_tokens += ct
                            yield {"type": "cost_update", "prompt_tokens": total_prompt_tokens, "completion_tokens": total_completion_tokens}

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tool_input = event.get("data", {}).get("input", {})
                    tools_used.append(tool_name)
                    yield {"type": "tool_start", "tool": tool_name, "args": tool_input if isinstance(tool_input, dict) else {}}

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    tool_output = event.get("data", {}).get("output", "")
                    output_preview = str(tool_output)[:200] if tool_output else ""
                    yield {"type": "tool_end", "tool": tool_name, "output_preview": output_preview}

            # [P0] v3 流结束后检查 interrupt（审批暂停）
            if hasattr(stream, 'interrupted') and stream.interrupted:
                interrupts = getattr(stream, 'interrupts', ()) or ()
                for intr in interrupts:
                    value = getattr(intr, 'value', intr) if not isinstance(intr, dict) else intr
                    if isinstance(value, dict) and value.get("type") == "approval_required":
                        yield {
                            "type": "approval_required",
                            "tool": value.get("tool", ""),
                            "args": value.get("args", {}),
                            "message": value.get("message", "需要用户确认"),
                        }
                    else:
                        # 通用 interrupt 格式
                        yield {
                            "type": "approval_required",
                            "tool": value.get("tool", "") if isinstance(value, dict) else str(value),
                            "args": value.get("args", {}) if isinstance(value, dict) else {},
                            "message": value.get("message", "需要用户确认") if isinstance(value, dict) else "需要用户确认",
                        }
                # 审批模式下不发 done，等 resume API 后续处理
                return

            # 发送上下文引用（从 context_engine 获取）
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
        # [P1] 双重检查锁：外层无锁快速检查，内层加锁防止并发初始化
        if self._initialized and self._graph is not None:
            return True
        async with self._init_lock:
            if self._initialized and self._graph is not None:
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
