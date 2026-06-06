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
    """通过 WebSocket 流式处理 Agent 对话"""
    from app.services.agent_service import agent_service

    content = data.get("content", "")
    conversation_id = data.get("conversationId", 0)

    if not content:
        await websocket.send_json({"type": "error", "message": "消息内容为空"})
        return

    if not agent_service.is_ready:
        await websocket.send_json({"type": "error", "message": "Agent 引擎未初始化"})
        return

    try:
        await websocket.send_json({"type": "start"})

        async for event in agent_service.chat_stream(
            conversation_id=conversation_id,
            user_id=user_id,
            messages=[{"role": "user", "content": content}],
        ):
            event_type = event.get("type", "")

            if event_type == "token":
                await websocket.send_json({"type": "token", "content": event["content"]})
            elif event_type == "tool_start":
                await websocket.send_json({"type": "tool_start", "tool": event["tool"]})
            elif event_type == "tool_end":
                await websocket.send_json({"type": "tool_end", "tool": event["tool"]})
            elif event_type == "done":
                await websocket.send_json({"type": "done"})
            elif event_type == "error":
                await websocket.send_json({"type": "error", "message": event["message"]})

    except Exception as e:
        logger.error(f"WebSocket Agent 对话失败: {e}", exc_info=True)
        await websocket.send_json({"type": "error", "message": str(e)})
