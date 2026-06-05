"""Agent 业务服务 — 封装 Agent 引擎的业务编排

职责:
  - 初始化 Agent 引擎（LLM + 工具 + 图）
  - 提供 Agent 对话接口（流式 / 非流式）
  - 管理 Agent 生命周期

注意:
  - 不含路由细节（路由层只做参数校验 + 调用本 service）
  - 不含 SQL 细节（通过 repository / mapper 操作数据）
"""
import json
from typing import Optional, AsyncIterator, Dict, Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentService:
    """Agent 业务服务"""

    def __init__(self):
        self._graph = None
        self._provider_id: Optional[int] = None
        self._model_name: str = ""

    @property
    def is_ready(self) -> bool:
        """Agent 引擎是否就绪"""
        return self._graph is not None

    async def initialize(self, db, provider_id: int, model_name: str = "") -> bool:
        """
        初始化 Agent 引擎。

        Args:
            db: 数据库会话
            provider_id: LLM 供应商 ID
            model_name: 模型名称（为空时用供应商默认）

        Returns:
            是否初始化成功
        """
        from app.agent.llm_service import llm_service
        from app.agent.tool_registry import tool_registry, register_builtin_tools
        from app.agent.engine import build_agent_graph

        try:
            # 注册内置工具
            register_builtin_tools()

            # 获取 LangChain LLM（绑定工具）
            llm = await llm_service.get_chat_llm(
                db,
                provider_id=provider_id,
                model_name=model_name,
                bind_tools=tool_registry.get_langchain_tools(),
            )

            # 构建 Agent 图
            self._graph = build_agent_graph(llm=llm, tool_registry=tool_registry)
            self._provider_id = provider_id
            self._model_name = model_name

            logger.info(f"Agent 引擎初始化完成 (provider_id={provider_id}, model={model_name})")
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
    ) -> Dict[str, Any]:
        """
        Agent 非流式对话。

        Args:
            conversation_id: 会话 ID
            user_id: 用户 ID
            messages: 消息列表 [{"role": "user", "content": "..."}]

        Returns:
            {"content": str, "tools_used": list, "iterations": int}
        """
        if not self.is_ready:
            raise RuntimeError("Agent 引擎未初始化")

        result = await self._graph.ainvoke({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "messages": messages,
            "context": "",
            "tool_calls": [],
            "tools_used": [],
            "final_answer": None,
            "iterations": 0,
            "needs_approval": False,
            "pending_tool_call": None,
        })

        return {
            "content": result.get("final_answer", "") or "",
            "tools_used": result.get("tools_used", []),
            "iterations": result.get("iterations", 0),
            "needs_approval": result.get("needs_approval", False),
            "pending_tool_call": result.get("pending_tool_call"),
        }

    async def chat_stream(
        self,
        conversation_id: int,
        user_id: int,
        messages: list,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Agent 流式对话，逐事件 yield。

        Yields:
            {"type": "token", "content": "..."}
            {"type": "tool_start", "tool": "..."}
            {"type": "tool_end", "tool": "..."}
            {"type": "done", "tools_used": [...]}
            {"type": "error", "message": "..."}
        """
        if not self.is_ready:
            yield {"type": "error", "message": "Agent 引擎未初始化"}
            return

        tools_used = []

        try:
            initial_state = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "messages": messages,
                "context": "",
                "tool_calls": [],
                "tools_used": [],
                "final_answer": None,
                "iterations": 0,
                "needs_approval": False,
                "pending_tool_call": None,
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

            yield {"type": "done", "tools_used": tools_used}

        except Exception as e:
            logger.error(f"Agent 流式对话失败: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}


# ── 全局单例 ──────────────────────────────────────────────

agent_service = AgentService()
