"""AI 对话 API — 流式 SSE 唯一路径

端点:
  - POST /chat — 流式对话（SSE + 心跳保活）
  - POST /chat/resume — 审批恢复（流式）
  - GET  /chat/tool-stats — 工具使用统计
"""
import asyncio
import json
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.services.agent_service import agent_service
from app.services.chat_service import ChatService
from app.services.llm_provider_service import LLMProviderService
from app.schemas.chat import ChatRequest
from app.schemas.response import ApiResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()
_chat_service = ChatService()
_provider_service = LLMProviderService()


async def _resolve_provider_id(db: AsyncSession, provider_id: int | None) -> int | None:
    if provider_id is not None:
        return provider_id
    default_provider = await _provider_service.get_default_provider(db)
    return default_provider.id if default_provider else None


class ResumeRequest(BaseModel):
    """审批恢复请求"""
    approved: bool
    tool_name: str = ""
    tool_args: Optional[dict] = None
    user_response: str = ""


class ChatRequestExtended(ChatRequest):
    """扩展聊天请求 — 新增 reasoning_depth"""
    reasoning_depth: Optional[str] = "balanced"


@router.post("/conversations/{conversation_id}/chat")
async def chat(
    request: Request,
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequestExtended = ...,
    db: AsyncSession = Depends(get_db),
):
    """对话入口 — 流式 SSE（唯一路径）"""
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("CONVERSATION_VALIDATION", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]
    model_name = data.model_name or ""
    user_id = getattr(data, "user_id", 0) or 0
    reasoning_depth = getattr(data, "reasoning_depth", "balanced") or "balanced"

    return StreamingResponse(
        _stream_response(conversation_id, user_id, messages, provider_id, model_name, reasoning_depth),
        media_type="text/event-stream",
    )


@router.post("/conversations/{conversation_id}/chat/resume")
async def chat_resume(
    conversation_id: int = Path(..., description="会话 ID"),
    data: ResumeRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    """
    审批恢复端点（interrupt/resume）— 按 LangGraph 官方规范实现。

    流程:
      1. Agent 遇到高风险工具 → interrupt() 暂停 → 前端弹出确认框
      2. 用户确认/拒绝 → 调用此端点
      3. 后端用 Command(resume=...) 恢复 Agent 执行
      4. 流式返回 Agent 后续执行结果

    LangGraph 官方模式:
      graph.astream(Command(resume=...), stream_mode=["messages","updates"], version="v2")
    """
    _full_content = []
    _queue: asyncio.Queue = asyncio.Queue()
    _stream_done = asyncio.Event()

    # 流开始前保存用户审批消息
    user_msg = data.user_response or f"[审批: {'批准' if data.approved else '拒绝'}] {data.tool_name}"
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as save_db:
            await _chat_service.save_skill_messages(
                save_db,
                conversation_id=conversation_id,
                user_content=user_msg,
                assistant_content="",
            )
            await save_db.commit()
    except Exception as e:
        logger.warning(f"保存审批消息失败: {e}")

    async def _save_assistant_message(content: str):
        """done 时保存助手回复"""
        if not content:
            return
        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as save_db:
                await _chat_service.save_skill_messages(
                    save_db,
                    conversation_id=conversation_id,
                    user_content="",
                    assistant_content=content,
                )
                await save_db.commit()
        except Exception as e:
            logger.warning(f"保存助手消息失败: {e}")

    async def _heartbeat():
        try:
            while not _stream_done.is_set():
                await asyncio.sleep(SSE_HEARTBEAT_INTERVAL)
                if not _stream_done.is_set():
                    await _queue.put(": heartbeat\n\n")
        except asyncio.CancelledError:
            pass

    async def _produce():
        try:
            async for event in agent_service.resume_stream(
                conversation_id=conversation_id,
                approved=data.approved,
                tool_name=data.tool_name,
                tool_args=data.tool_args,
                user_response=data.user_response,
            ):
                event_type = event.get("type", "")
                if event_type == "token":
                    _full_content.append(event.get("content", ""))
                    await _queue.put(f"data: {json.dumps({'content': event['content'], 'done': False})}\n\n")
                elif event_type == "tool_start":
                    await _queue.put(f"data: {json.dumps({'tool_start': event['tool'], 'tool_args': event.get('args', {}), 'done': False})}\n\n")
                elif event_type == "tool_end":
                    await _queue.put(f"data: {json.dumps({'tool_end': event['tool'], 'output_preview': event.get('output_preview', ''), 'done': False})}\n\n")
                elif event_type == "progress":
                    progress = {k: v for k, v in event.items() if k != "type"}
                    await _queue.put(f"data: {json.dumps({'progress': progress, 'done': False})}\n\n")
                elif event_type == "done":
                    # done 时保存助手回复（数据完整）
                    await _save_assistant_message("".join(_full_content))
                    await _queue.put(f"data: {json.dumps({'content': '', 'done': True, 'tools_used': event.get('tools_used', []), 'duration_ms': event.get('duration_ms', 0)})}\n\n")
                elif event_type == "error":
                    await _queue.put(f"data: {json.dumps({'error': event['message'], 'done': True})}\n\n")
        except Exception as e:
            logger.error(f"Resume 流式对话失败: {e}", exc_info=True)
            await _queue.put(f"data: {json.dumps({'error': str(e), 'done': True})}\n\n")
        finally:
            _stream_done.set()
            await _queue.put(None)

    heartbeat_task = asyncio.create_task(_heartbeat())
    producer_task = asyncio.create_task(_produce())

    async def _sse_generator():
        try:
            while True:
                item = await _queue.get()
                if item is None:
                    break
                yield item
        finally:
            heartbeat_task.cancel()
            producer_task.cancel()

    return StreamingResponse(_sse_generator(), media_type="text/event-stream")


@router.get("/chat/tool-stats")
async def tool_stats() -> ApiResult[dict]:
    """工具使用统计"""
    stats = agent_service.get_tool_stats()
    return ApiResult(data=stats)


SSE_HEARTBEAT_INTERVAL = 15  # 心跳间隔（秒），小于 nginx 默认 60s proxy_read_timeout


async def _stream_response(
    conversation_id: int, user_id: int, messages: list,
    provider_id: int, model_name: str, reasoning_depth: str = "balanced",
):
    """SSE 流式响应 — 带心跳保活 + 消息持久化

    消息保存策略（业内标准）:
      - 用户消息：流开始前保存（确保不丢）
      - 助手回复：done 事件时保存（数据完整 + 携带 token 统计）
      - 流中断/报错：助手回复不保存（前端本地有 token，刷新后丢失是预期行为）

    心跳机制（业内规范）:
      - 发送 SSE 注释行 ': heartbeat\\n\\n'，不触发前端 onmessage
      - 间隔 15s（< nginx 60s proxy_read_timeout）
      - 用 asyncio.Queue 合并心跳和业务事件到同一个生成器
    """
    _full_content = []
    _queue: asyncio.Queue = asyncio.Queue()
    _stream_done = asyncio.Event()

    # 流开始前保存用户消息（独立事务，确保不丢）
    user_content = messages[-1]["content"] if messages else ""
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as save_db:
            await _chat_service.save_skill_messages(
                save_db,
                conversation_id=conversation_id,
                user_content=user_content,
                assistant_content="",  # 仅保存用户消息
            )
            await save_db.commit()
    except Exception as e:
        logger.warning(f"保存用户消息失败: {e}")

    async def _heartbeat():
        """心跳协程 — 定期发送 SSE 注释保活"""
        try:
            while not _stream_done.is_set():
                await asyncio.sleep(SSE_HEARTBEAT_INTERVAL)
                if not _stream_done.is_set():
                    await _queue.put(": heartbeat\n\n")
        except asyncio.CancelledError:
            pass

    async def _save_assistant_message(content: str, token_count: int):
        """done 时保存助手回复（独立事务）"""
        if not content:
            return
        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as save_db:
                await _chat_service.save_skill_messages(
                    save_db,
                    conversation_id=conversation_id,
                    user_content="",  # 仅保存助手回复
                    assistant_content=content,
                    token_count=token_count,
                )
                await save_db.commit()
        except Exception as e:
            logger.warning(f"保存助手消息失败: {e}")

    async def _produce():
        """业务事件生产者 — 从 agent_service 读取事件放入队列"""
        try:
            async for event in agent_service.chat_stream(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=messages,
                provider_id=provider_id,
                model_name=model_name,
                reasoning_depth=reasoning_depth,
            ):
                event_type = event.get("type", "")
                if event_type == "token":
                    _full_content.append(event.get("content", ""))
                    await _queue.put(f"data: {json.dumps({'content': event['content'], 'done': False})}\n\n")
                elif event_type == "tool_start":
                    await _queue.put(f"data: {json.dumps({'tool_start': event['tool'], 'tool_args': event.get('args', {}), 'done': False})}\n\n")
                elif event_type == "tool_end":
                    await _queue.put(f"data: {json.dumps({'tool_end': event['tool'], 'output_preview': event.get('output_preview', ''), 'done': False})}\n\n")
                elif event_type == "intent_hit":
                    await _queue.put(f"data: {json.dumps({'intent_hit': event['intent'], 'intent_score': event.get('score', 0), 'done': False})}\n\n")
                elif event_type == "cost_update":
                    await _queue.put(f"data: {json.dumps({'cost': {'prompt_tokens': event['prompt_tokens'], 'completion_tokens': event['completion_tokens']}, 'done': False})}\n\n")
                elif event_type == "approval_required":
                    await _queue.put(f"data: {json.dumps({'approval_required': {'tool': event.get('tool', ''), 'args': event.get('args', {}), 'message': event.get('message', '')}, 'done': False})}\n\n")
                elif event_type == "progress":
                    # Agent 执行进展事件（AG-UI 协议兼容）
                    progress = {k: v for k, v in event.items() if k != "type"}
                    await _queue.put(f"data: {json.dumps({'progress': progress, 'done': False})}\n\n")
                elif event_type == "done":
                    prompt_tokens = event.get("prompt_tokens", 0)
                    completion_tokens = event.get("completion_tokens", 0)
                    total_tokens = prompt_tokens + completion_tokens
                    # done 时保存助手回复（数据完整）
                    await _save_assistant_message("".join(_full_content), total_tokens)
                    await _queue.put(f"data: {json.dumps({'content': '', 'done': True, 'tools_used': event.get('tools_used', []), 'duration_ms': event.get('duration_ms', 0), 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens})}\n\n")
                elif event_type == "error":
                    await _queue.put(f"data: {json.dumps({'error': event['message'], 'done': True})}\n\n")
        except Exception as e:
            logger.error(f"流式对话失败: {e}", exc_info=True)
            await _queue.put(f"data: {json.dumps({'error': str(e), 'done': True})}\n\n")
        finally:
            _stream_done.set()
            await _queue.put(None)  # 哨兵值，通知消费者结束

    # 启动心跳和生产者协程
    heartbeat_task = asyncio.create_task(_heartbeat())
    producer_task = asyncio.create_task(_produce())

    try:
        # 消费者循环 — 从队列读取事件并 yield
        while True:
            item = await _queue.get()
            if item is None:
                break
            yield item
    finally:
        heartbeat_task.cancel()
        producer_task.cancel()
