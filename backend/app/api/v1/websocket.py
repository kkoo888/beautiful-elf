"""WebSocket 路由"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import ws_manager
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws")
@router.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str = "default"):
    """
    WebSocket 连接端点
    /ws          → 默认 channel (default)
    /ws/{channel} → 指定 channel: chat, pet, notification, system 等
    """
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_json()
            # 回显 + 广播
            await ws_manager.send_to(websocket, {"type": "ack", "data": data})
            await ws_manager.broadcast(channel, {"type": "message", "from": channel, "data": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
        ws_manager.disconnect(websocket, channel)
