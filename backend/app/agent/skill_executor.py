"""技能执行器 — 桥接技能定义与 LangChain Tool Calling

架构:
  意图命中 target_module → SkillExecutor.execute()
    ├─ 技能有 tools → 注册到 ToolRegistry → Agent 图（Tool Calling）
    └─ 技能无 tools → LLM + 技能描述上下文

技能 config.tools 格式:
  {
    "tools": [
      {
        "name": "get_weather",
        "description": "查询天气",
        "parameters": {
          "type": "object",
          "properties": {"city": {"type": "string"}},
          "required": ["city"]
        },
        "endpoint": "https://api.weather.com/v1/query",
        "method": "GET"
      }
    ]
  }
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


class SkillExecutor:
    """技能执行器"""

    async def execute(
        self,
        db: AsyncSession,
        skill_name: str,
        user_message: str,
        messages: List[dict],
        provider_id: Optional[int] = None,
        model_name: str = "",
        context_engine=None,
        memory_manager=None,
    ) -> str:
        """
        执行技能。

        Args:
            db: 数据库会话
            skill_name: 技能名称（target_module）
            user_message: 用户最新消息
            messages: 完整对话历史
            provider_id: LLM 供应商 ID（可选，不传用默认）
            model_name: 模型名称
            context_engine: 上下文引擎（可选，用于 RAG 检索）
            memory_manager: 记忆管理器（可选，用于相关记忆检索）

        Returns:
            技能执行结果（文本）
        """
        # 1. 查找技能
        from app.services.skill_service import SkillService
        skill_service = SkillService()

        skill = await self._find_skill(db, skill_service, skill_name)
        if not skill:
            logger.warning(f"技能 '{skill_name}' 不存在，降级走 LLM")
            return await self._fallback_llm(
                db, user_message, messages, provider_id, model_name,
                context_engine=context_engine, memory_manager=memory_manager,
            )

        config = skill.config or {}
        tool_defs = config.get("tools", [])
        skill_description = skill.description or skill.display_name or skill_name

        # 2. 有工具定义 → Agent 图 + Tool Calling
        if tool_defs:
            return await self._execute_with_tools(
                db, skill_name, skill_description, tool_defs,
                user_message, messages, provider_id, model_name,
            )

        # 3. 无工具 → LLM + 技能上下文 + 记忆/RAG
        return await self._execute_with_context(
            db, skill_name, skill_description, config,
            user_message, messages, provider_id, model_name,
            context_engine=context_engine, memory_manager=memory_manager,
        )

    async def _find_skill(self, db, skill_service, skill_name):
        """按 name 查技能"""
        try:
            from app.repository.skill_repo import SkillRepository
            repo = SkillRepository()
            return await repo.find_by_name(db, skill_name)
        except Exception as e:
            logger.error(f"查找技能 '{skill_name}' 失败: {e}")
            return None

    async def _execute_with_tools(
        self, db, skill_name, skill_description, tool_defs,
        user_message, messages, provider_id, model_name,
    ) -> str:
        """有工具：注册到 ToolRegistry → Agent 图执行"""
        import time
        from app.agent.tool_registry import tool_registry
        from app.agent.engine import build_agent_graph
        from app.agent.llm_service import llm_service
        from app.services.llm_provider_service import LLMProviderService

        t0 = time.time()
        temp_tool_names = []

        try:
            # 注册技能工具到全局 ToolRegistry（临时）
            for td in tool_defs:
                name = td["name"]
                temp_tool_names.append(name)
                tool_registry.register(
                    name=name,
                    func=self._make_http_executor(td),
                    description=td.get("description", ""),
                    parameters=td.get("parameters", {"type": "object", "properties": {}}),
                    risk_level=td.get("risk_level", "low"),
                    module=f"skill:{skill_name}",
                )

            # 解析 provider_id
            if provider_id is None:
                provider_service = LLMProviderService()
                default = await provider_service.get_default_provider(db)
                provider_id = default.id if default else None
            if provider_id is None:
                return "⚠️ 请先选择 AI 供应商"

            # 构建 LangChain LLM + 绑定工具
            lc_tools = tool_registry.get_langchain_tools()
            llm = await llm_service.get_chat_llm(
                db, provider_id=provider_id, model_name=model_name,
                bind_tools=lc_tools,
            )

            # 构建 Agent 图
            graph = build_agent_graph(llm=llm, tool_registry=tool_registry)

            # 执行
            result = await graph.ainvoke({
                "conversation_id": 0,
                "user_id": 0,
                "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
                "context": f"【技能：{skill_name}】{skill_description}",
                "tool_calls": [],
                "tools_used": [],
                "final_answer": None,
                "iterations": 0,
                "needs_approval": False,
                "pending_tool_call": None,
            })

            elapsed = time.time() - t0
            logger.info(f"[SkillExecutor] '{skill_name}' 完成 elapsed={elapsed:.2f}s tools={result.get('tools_used', [])}")

            return result.get("final_answer") or "技能执行完成，但未生成回答。"

        finally:
            # 清理临时注册的工具
            for name in temp_tool_names:
                if name in tool_registry._tools:
                    del tool_registry._tools[name]

    async def _execute_with_context(
        self, db, skill_name, skill_description, config,
        user_message, messages, provider_id, model_name,
        context_engine=None, memory_manager=None,
    ) -> str:
        """无工具：LLM + 技能描述 + 记忆/RAG 上下文"""
        from app.services.llm_chat_service import llm_chat_service
        from app.services.llm_provider_service import LLMProviderService

        # 解析 provider_id
        if provider_id is None:
            provider_service = LLMProviderService()
            default = await provider_service.get_default_provider(db)
            provider_id = default.id if default else None
        if provider_id is None:
            return "⚠️ 请先选择 AI 供应商"

        # 组装上下文（记忆 + RAG）
        context_parts = [f"技能说明：{skill_description}"]

        if memory_manager:
            try:
                memories = await memory_manager.search(user_message, limit=3)
                if memories:
                    memory_text = "\n".join(f"- {m.content}" for m in memories if m.content)
                    context_parts.append(f"相关记忆：\n{memory_text}")
            except Exception as e:
                logger.debug(f"记忆检索失败（跳过）: {e}")

        if context_engine:
            try:
                rag_results = await context_engine.retrieve(user_message, top_k=3)
                if rag_results:
                    rag_text = "\n".join(f"- {r.get('content', '')}" for r in rag_results if r.get('content'))
                    context_parts.append(f"知识库参考：\n{rag_text}")
            except Exception as e:
                logger.debug(f"RAG 检索失败（跳过）: {e}")

        # 注入技能上下文到 system message
        system_msg = {
            "role": "system",
            "content": (
                f"你现在使用技能「{skill_name}」回答用户问题。\n"
                f"{chr(10).join(context_parts)}\n"
                f"请根据以上上下文回答用户问题。"
            ),
        }
        enriched_messages = [system_msg] + messages

        result = await llm_chat_service.chat(
            db, provider_id=provider_id, model_name=model_name,
            messages=enriched_messages, temperature=0.7, max_tokens=2048,
        )
        if result.error:
            logger.warning(f"技能 '{skill_name}' LLM 调用失败: {result.error}")
        return result.content

    async def _fallback_llm(
        self, db, user_message, messages, provider_id, model_name,
        context_engine=None, memory_manager=None,
    ) -> str:
        """降级：纯 LLM 对话 + 可用上下文"""
        from app.services.llm_chat_service import llm_chat_service
        from app.services.llm_provider_service import LLMProviderService

        if provider_id is None:
            provider_service = LLMProviderService()
            default = await provider_service.get_default_provider(db)
            provider_id = default.id if default else None
        if provider_id is None:
            return "⚠️ 请先选择 AI 供应商"

        # 降级时也尝试注入记忆上下文
        context_parts = []
        if memory_manager:
            try:
                memories = await memory_manager.search(user_message, limit=3)
                if memories:
                    memory_text = "\n".join(f"- {m.content}" for m in memories if m.content)
                    context_parts.append(f"相关记忆：\n{memory_text}")
            except Exception:
                pass

        enriched_messages = messages
        if context_parts:
            system_msg = {"role": "system", "content": "\n".join(context_parts)}
            enriched_messages = [system_msg] + messages

        result = await llm_chat_service.chat(
            db, provider_id=provider_id, model_name=model_name,
            messages=enriched_messages, temperature=0.7, max_tokens=2048,
        )
        if result.error:
            logger.warning(f"降级 LLM 调用失败: {result.error}")
        return result.content

    @staticmethod
    def _make_http_executor(tool_def: dict):
        """根据工具定义创建 HTTP 执行函数"""
        import httpx

        async def http_executor(**kwargs) -> str:
            endpoint = tool_def.get("endpoint", "")
            method = (tool_def.get("method", "GET")).upper()
            headers = tool_def.get("headers", {})
            timeout = tool_def.get("timeout", 10)

            if not endpoint:
                return f"工具 '{tool_def['name']}' 未配置 endpoint"

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method == "GET":
                        resp = await client.get(endpoint, params=kwargs, headers=headers)
                    elif method == "POST":
                        resp = await client.post(endpoint, json=kwargs, headers=headers)
                    else:
                        resp = await client.request(method, endpoint, json=kwargs, headers=headers)

                    resp.raise_for_status()
                    return resp.text[:5000]
            except httpx.HTTPStatusError as e:
                return f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            except Exception as e:
                return f"请求失败: {e}"

        return http_executor


# ── 全局单例 ──────────────────────────────────────────────

skill_executor = SkillExecutor()
