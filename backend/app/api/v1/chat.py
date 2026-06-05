"""AI 对话 API — 支持 Agent 引擎 + 纯 LLM 对话

Agent 模式（默认）:
  用户消息 → 意图路由（TODO） → Agent引擎 → 工具调用 → 返回回答

纯 LLM 模式（stream=true 且无 Agent）:
  用户消息 → LLM 直接对话 → SSE 流式返回
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.services.llm_chat_service import LLMChatService
from app.services.llm_provider_service import LLMProviderService
from app.services.message_service import MessageService
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.message import MessageCreate
from app.schemas.response import ApiResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()
_llm_chat_service = LLMChatService()
_provider_service = LLMProviderService()
_msg_service = MessageService()


async def _resolve_provider_id(db: AsyncSession, provider_id: int | None) -> int | None:
    """解析供应商 ID：前端未传时自动使用默认供应商"""
    if provider_id is not None:
        return provider_id
    default_provider = await _provider_service.get_default(db)
    return default_provider.id if default_provider else None


# ── Agent 对话 ────────────────────────────────────────────

@router.post("/conversations/{conversation_id}/chat", response_model=ApiResult[ChatResponse])
async def chat(
    request: Request,
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequest = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[ChatResponse]:
    """Agent 对话 — 自动选择 Agent 模式或纯 LLM 模式"""
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("NO_PROVIDER", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]

    # 尝试使用 Agent 引擎
    agent_graph = getattr(request.app.state, "agent_graph", None)

    if agent_graph is not None:
        # Agent 模式
        if data.stream:
            return StreamingResponse(
                _agent_stream_generator(
                    agent_graph, conversation_id, provider_id, data, messages, db
                ),
                media_type="text/event-stream",
            )
        else:
            return await _agent_chat(agent_graph, conversation_id, provider_id, data, messages, db)

    # 降级：纯 LLM 模式
    if data.stream:
        return StreamingResponse(
            _stream_generator(conversation_id, provider_id, data, messages),
            media_type="text/event-stream",
        )

    try:
        result = await _llm_chat_service.chat(
            db,
            provider_id=provider_id,
            model_name=data.model_name,
            messages=messages,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
        )
        try:
            await _msg_service.create(db, MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=result.content,
                token_count=result.token_count,
            ))
        except Exception:
            pass
        return ApiResult(data=result)
    except Exception as e:
        return api_error("AI_TIMEOUT", str(e), "请检查模型配置或稍后重试")


# ── Agent 非流式 ──────────────────────────────────────────

async def _agent_chat(
    agent_graph, conversation_id: int, provider_id: int, data: ChatRequest, messages: list, db: AsyncSession
) -> ApiResult:
    """Agent 非流式对话"""
    from app.core.dependencies import get_current_user_id
    from app.agent.llm_service import llm_service

    try:
        # 获取带工具绑定的 LLM
        from app.agent.tool_registry import tool_registry, register_builtin_tools
        register_builtin_tools()

        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=data.model_name,
            temperature=data.temperature, max_tokens=data.max_tokens,
            bind_tools=tool_registry.get_langchain_tools(),
        )

        # 重新构建图（使用当前 LLM）
        from app.agent.engine import build_agent_graph
        graph = build_agent_graph(llm=llm, tool_registry=tool_registry)

        # 运行 Agent
        result = await graph.ainvoke({
            "conversation_id": conversation_id,
            "user_id": 0,
            "messages": messages,
            "context": "",
            "tool_calls": [],
            "tools_used": [],
            "final_answer": None,
            "iterations": 0,
            "needs_approval": False,
            "pending_tool_call": None,
        })

        final_answer = result.get("final_answer", "") or ""
        tools_used = result.get("tools_used", [])

        # 保存消息
        try:
            await _msg_service.create(db, MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=final_answer,
            ))
        except Exception:
            pass

        return ApiResult(data=ChatResponse(
            content=final_answer,
            model=data.model_name,
            provider_type="agent",
            token_count=0,
        ))

    except Exception as e:
        logger.error(f"Agent 对话失败: {e}", exc_info=True)
        return api_error("AGENT_ERROR", str(e), "Agent 对话失败，请检查配置")


# ── Agent 流式 ────────────────────────────────────────────

async def _agent_stream_generator(
    agent_graph, conversation_id: int, provider_id: int, data: ChatRequest, messages: list, db: AsyncSession
):
    """Agent SSE 流式输出"""
    from app.agent.llm_service import llm_service
    from app.agent.tool_registry import tool_registry, register_builtin_tools

    full_content = ""
    tools_used = []

    try:
        register_builtin_tools()

        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=data.model_name,
            temperature=data.temperature, max_tokens=data.max_tokens,
            bind_tools=tool_registry.get_langchain_tools(),
        )

        from app.agent.engine import build_agent_graph
        graph = build_agent_graph(llm=llm, tool_registry=tool_registry)

        initial_state = {
            "conversation_id": conversation_id,
            "user_id": 0,
            "messages": messages,
            "context": "",
            "tool_calls": [],
            "tools_used": [],
            "final_answer": None,
            "iterations": 0,
            "needs_approval": False,
            "pending_tool_call": None,
        }

        # 使用 astream_events 获取流式事件
        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    token = chunk.content
                    full_content += token
                    yield f"data: {json.dumps({'content': token, 'done': False})}\n\n"

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tools_used.append(tool_name)
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool_name})}\n\n"

        # 完成
        yield f"data: {json.dumps({'content': '', 'done': True, 'tools_used': tools_used})}\n\n"

        # 保存消息
        if full_content:
            try:
                async with AsyncSessionLocal() as save_db:
                    await _msg_service.create(save_db, MessageCreate(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=full_content,
                    ))
                    await save_db.commit()
            except Exception as e:
                logger.warning(f"Agent 流式保存消息失败: {e}")

    except Exception as e:
        logger.error(f"Agent 流式对话失败: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"


# ── 纯 LLM 流式（降级）────────────────────────────────────

async def _stream_generator(
    conversation_id: int, provider_id: int, data: ChatRequest, messages: list,
):
    """纯 LLM SSE 流式生成器（降级模式）"""
    full_content = ""
    try:
        async with AsyncSessionLocal() as db:
            async for chunk in _llm_chat_service.chat_stream(
                db,
                provider_id=provider_id,
                model_name=data.model_name,
                messages=messages,
                temperature=data.temperature,
                max_tokens=data.max_tokens,
            ):
                full_content += chunk
                yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"

            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"

            try:
                await _msg_service.create(db, MessageCreate(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
                    token_count=0,
                ))
                await db.commit()
            except Exception:
                pass
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
