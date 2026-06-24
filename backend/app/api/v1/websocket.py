"""WebSocket 路由 — 支持 Agent 流式输出 + JWT 鉴权"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket_manager import ws_manager
from app.core.security import decode_access_token
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def _authenticate_ws(websocket: WebSocket, token: str | None) -> int | None:
    """
    WebSocket JWT 鉴权。

    有 token → 验证并返回 user_id
    无 token → 返回 0（guest 模式，本地开发用）

    Returns:
        user_id: 认证成功返回用户 ID，失败返回 None
    """
    if not token:
        # 无 token，允许 guest 连接（本地开发模式）
        logger.info("WebSocket 无 token，以 guest 模式连接")
        return 0

    payload = decode_access_token(token)
    if not payload:
        # decode_access_token 内部已记录具体失败原因
        return None

    user_id = payload.get("user_id") or payload.get("sub")
    if user_id is not None:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            pass

    return None


@router.websocket("/ws")
@router.websocket("/ws/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str = "default",
    token: str | None = Query(default=None, description="JWT 认证 token"),
):
    """
    WebSocket 连接端点

    鉴权方式: ?token=<jwt>
    鉴权失败: 返回 403 关闭连接
    鉴权成功: user_id 附加到 websocket.state

    /ws          → 默认 channel (default)
    /ws/{channel} → 指定 channel: chat, pet, notification, system 等
    """
    # JWT 鉴权（无 token 时允许 guest 连接）
    user_id = await _authenticate_ws(websocket, token)
    if user_id is None:
        # token 存在但验证失败 → 拒绝
        await websocket.close(code=4003, reason="AUTH_UNAUTHORIZED: 无效的 token")
        logger.warning(f"WebSocket 鉴权失败（token 无效）: channel={channel}")
        return

    # 鉴权通过，存储 user_id
    websocket.state.user_id = user_id
    logger.info(f"WebSocket 连接: channel={channel} user_id={user_id}")

    await ws_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_json()

            # 心跳
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Agent 对话消息（通过 WebSocket 流式输出）
            if data.get("type") == "chat" and channel == "chat":
                await _handle_agent_ws(websocket, data, user_id)
                continue

            # 其他消息广播
            await ws_manager.broadcast(channel, data)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
        logger.info(f"WebSocket 断开: channel={channel} user_id={user_id}")


async def _handle_agent_ws(websocket: WebSocket, data: dict, user_id: int):
    """通过 WebSocket 流式处理 Agent 对话（v6.3: 队列缓冲 + 心跳 + 全事件支持）"""
    import asyncio
    from app.services.agent_service import agent_service

    content = data.get("content", "")
    conversation_id = data.get("conversationId", 0)
    provider_id = data.get("providerId")
    model_name = data.get("modelName", "")
    reasoning_depth = data.get("reasoningDepth", "balanced")
    goal_mode = data.get("goalMode", False)
    goal_definition = data.get("goalDefinition", "")
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("maxTokens", 2048)

    if not content:
        await websocket.send_json({"type": "error", "message": "消息内容为空"})
        return

    # 懒初始化 Agent 引擎
    if not agent_service.is_ready:
        success = await agent_service._lazy_init(provider_id, model_name)
        if not success:
            await websocket.send_json({"type": "error", "message": "Agent 引擎初始化失败"})
            return

    # ── 队列 + 后台任务 + 心跳 ──
    _queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    _stream_done = asyncio.Event()

    async def _produce():
        """生产者：Agent 执行 → 事件写入队列"""
        try:
            async for event in agent_service.chat_stream(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=[{"role": "user", "content": content}],
                provider_id=provider_id,
                model_name=model_name,
                reasoning_depth=reasoning_depth,
                goal_mode=goal_mode,
                goal_definition=goal_definition,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                if _stream_done.is_set():
                    break
                event_type = event.get("type", "")

                if event_type == "token":
                    await _queue.put({"type": "token", "content": event["content"]})
                elif event_type == "tool_start":
                    await _queue.put({"type": "tool_start", "tool": event["tool"], "args": event.get("args", {})})
                elif event_type == "tool_end":
                    await _queue.put({"type": "tool_end", "tool": event["tool"], "output_preview": event.get("output_preview", "")})
                elif event_type == "tool_error":
                    await _queue.put({"type": "tool_error", "tool": event["tool"], "output_preview": event.get("output_preview", "")})
                elif event_type == "progress":
                    progress = {k: v for k, v in event.items() if k != "type"}
                    await _queue.put({"type": "progress", **progress})
                elif event_type == "goal_subtasks":
                    await _queue.put({"type": "goal_subtasks", "subtasks": event.get("subtasks", [])})
                elif event_type == "goal_tool_update":
                    await _queue.put({"type": "goal_tool_update", "task_id": event.get("task_id", 0), "tool": event.get("tool", ""), "tool_status": event.get("tool_status", ""), "args": event.get("args", {}), "output_preview": event.get("output_preview", "")})
                elif event_type == "intent_hit":
                    await _queue.put({"type": "intent_hit", "intent": event["intent"], "score": event.get("score", 0)})
                elif event_type == "cost_update":
                    await _queue.put({"type": "cost_update", "prompt_tokens": event["prompt_tokens"], "completion_tokens": event["completion_tokens"]})
                elif event_type == "approval_required":
                    await _queue.put({"type": "approval_required", "tool": event.get("tool", ""), "args": event.get("args", {}), "message": event.get("message", "")})
                elif event_type == "done":
                    await _queue.put({"type": "done", "tools_used": event.get("tools_used", []), "duration_ms": event.get("duration_ms", 0), "prompt_tokens": event.get("prompt_tokens", 0), "completion_tokens": event.get("completion_tokens", 0), "goal_subtasks": event.get("goal_subtasks", [])})
                elif event_type == "error":
                    await _queue.put({"type": "error", "message": event["message"]})

        except Exception as e:
            logger.error(f"WebSocket Agent 生产者失败: {e}", exc_info=True)
            await _queue.put({"type": "error", "message": str(e)})
        finally:
            _stream_done.set()
            await _queue.put(None)  # 哨兵值

    async def _heartbeat():
        """心跳：每 15s 发送 ping，防止中间层超时断连"""
        try:
            while not _stream_done.is_set():
                await asyncio.sleep(15)
                if not _stream_done.is_set():
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        break
        except asyncio.CancelledError:
            pass

    # 启动生产者和心跳
    producer_task = asyncio.create_task(_produce())
    heartbeat_task = asyncio.create_task(_heartbeat())

    try:
        await websocket.send_json({"type": "start"})

        # 消费者：从队列读取事件并发送
        while True:
            item = await _queue.get()
            if item is None:
                break
            try:
                await websocket.send_json(item)
            except Exception:
                logger.warning("WebSocket 发送失败，客户端可能已断开")
                _stream_done.set()
                break

    except WebSocketDisconnect:
        logger.info("WebSocket 客户端断开")
        _stream_done.set()
    except Exception as e:
        logger.error(f"WebSocket Agent 对话失败: {e}", exc_info=True)
        _stream_done.set()
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        _stream_done.set()
        heartbeat_task.cancel()
        producer_task.cancel()
        try:
            await heartbeat_task
        except (asyncio.CancelledError, Exception):
            pass
        try:
            await producer_task
        except (asyncio.CancelledError, Exception):
            pass
