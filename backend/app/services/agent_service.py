"""Agent 业务服务 — 封装 Agent 引擎的业务编排（v2 重构）

重构点:
  1. 初始化时注入所有依赖（ContextEngine, IntentRouter, MemoryManager 等）
  2. Agent 图包含意图路由（不再是外部系统）
  3. 流式/非流式统一走 Agent 图
  4. 完整追踪（AgentTrace）

遵循规范:
  - 分层架构: service 调用 agent 模块，不含路由细节
  - 统一异常: 不吞异常，向上传播
"""
import json
import time
from typing import Optional, AsyncIterator, Dict, Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentService:
    """Agent 业务服务（v2）"""

    def __init__(self):
        self._graph = None
        self._provider_id: Optional[int] = None
        self._model_name: str = ""
        self._initialized = False

    @property
    def is_ready(self) -> bool:
        """Agent 引擎是否就绪"""
        return self._graph is not None

    async def initialize(
        self,
        db,
        provider_id: int,
        model_name: str = "",
        tool_names: Optional[list] = None,
    ) -> bool:
        """
        初始化 Agent 引擎（v2）。

        注入所有依赖: LLM + ToolRegistry + ContextEngine + IntentRouter + MemoryManager

        Args:
            db: 数据库会话
            provider_id: LLM 供应商 ID
            model_name: 模型名称（为空时用供应商默认）
            tool_names: 指定绑定的工具名列表（为 None 时绑定全部）

        Returns:
            是否初始化成功
        """
        from app.agent.llm_service import llm_service
        from app.agent.tool_registry import tool_registry, register_builtin_tools
        from app.agent.engine import build_agent_graph
        from app.agent.context_engine import ContextEngine
        from app.services.memory_service import memory_service
        from app.services.intent_service import intent_service

        try:
            # 1. 注册内置工具
            register_builtin_tools()

            # 2. 从 DB 加载工具
            await tool_registry.load_from_db(db)

            # 3. 获取 LangChain LLM（绑定指定工具）
            lc_tools = tool_registry.get_langchain_tools(tool_names)
            llm = await llm_service.get_chat_llm(
                db,
                provider_id=provider_id,
                model_name=model_name,
                bind_tools=lc_tools,
            )

            # 4. 获取各子系统
            memory_manager = memory_service.memory_manager
            intent_router = intent_service.intent_router

            # 5. 创建 ContextEngine
            context_engine = ContextEngine(
                memory_manager=memory_manager,
                rag_pipeline=None,  # RAG 在 context_engine 内部可选注入
            )

            # 6. 构建 Agent 图（v2，包含意图路由）
            self._graph = build_agent_graph(
                llm=llm,
                tool_registry=tool_registry,
                context_engine=context_engine,
                memory_manager=memory_manager,
                intent_router=intent_router,
                skill_executor=None,  # 技能执行器在图内独立创建
                rag_pipeline=None,
            )
            self._provider_id = provider_id
            self._model_name = model_name
            self._initialized = True

            logger.info(f"Agent 引擎 v2 初始化完成 (provider_id={provider_id}, model={model_name}, tools={len(lc_tools)})")
            return True

        except ImportError as e:
            logger.warning(f"缺少 LangChain 依赖，Agent 降级为纯 LLM 模式: {e}")
            self._graph = None
            return False
        except Exception as e:
            logger.error(f"Agent 引擎初始化失败: {e}", exc_info=True)
            self._graph = None
            return False

    async def chat(
        self,
        conversation_id: int,
        user_id: int,
        messages: list,
        provider_id: int = 0,
        model_name: str = "",
    ) -> Dict[str, Any]:
        """
        Agent 非流式对话。

        所有消息统一走 Agent 图（包含意图路由 → Context 组装 → LLM → 工具执行）。
        """
        if not self.is_ready:
            success = await self._lazy_init(provider_id, model_name)
            if not success:
                raise RuntimeError("Agent 引擎初始化失败")

        t0 = time.time()

        result = await self._graph.ainvoke({
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
        })

        elapsed = int((time.time() - t0) * 1000)

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
            context_sources=result.get("trace_metadata", {}).get("context_sources", []),
        ))

        return {
            "content": result.get("final_answer") or "",
            "tools_used": result.get("tools_used", []),
            "iterations": result.get("iterations", 0),
            "needs_approval": result.get("needs_approval", False),
            "pending_tool_call": result.get("pending_tool_call"),
            "intent": result.get("intent"),
            "duration_ms": elapsed,
        }

    async def chat_stream(
        self,
        conversation_id: int,
        user_id: int,
        messages: list,
        provider_id: int = 0,
        model_name: str = "",
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Agent 流式对话。

        Yields:
            {"type": "token", "content": "..."}
            {"type": "tool_start", "tool": "..."}
            {"type": "tool_end", "tool": "..."}
            {"type": "done", "tools_used": [...]}
            {"type": "error", "message": "..."}
        """
        if not self.is_ready:
            success = await self._lazy_init(provider_id, model_name)
            if not success:
                yield {"type": "error", "message": "Agent 引擎初始化失败"}
                return

        t0 = time.time()
        tools_used = []

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
            }

            async for event in self._graph.astream_events(initial_state, version="v2"):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield {"type": "token", "content": chunk.content}

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tools_used.append(tool_name)
                    yield {"type": "tool_start", "tool": tool_name}

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    yield {"type": "tool_end", "tool": tool_name}

            elapsed = int((time.time() - t0) * 1000)
            yield {"type": "done", "tools_used": tools_used, "duration_ms": elapsed}

        except Exception as e:
            logger.error(f"Agent 流式对话失败: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}

    async def _lazy_init(self, provider_id: int, model_name: str) -> bool:
        """懒加载：首次对话时自动初始化 Agent 引擎"""
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await self.initialize(db, provider_id=provider_id, model_name=model_name)

    def reset(self):
        """重置 Agent 引擎（切换模型时调用）"""
        self._graph = None
        self._provider_id = None
        self._model_name = ""
        self._initialized = False
        logger.info("Agent 引擎已重置，下次对话时重新初始化")


# ── 全局单例 ──────────────────────────────────────────────
agent_service = AgentService()
