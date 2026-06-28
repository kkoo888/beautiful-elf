"""WebSocket 连接管理器"""
import json
from typing import Dict, Set
from fastapi import WebSocket
from app.core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """
    管理所有 WebSocket 连接
    - 按 channel 分组（如 chat、pet、notification）
    - 支持广播、定向发送
    """

    def __init__(self):
        # channel -> set of websockets
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "default", _already_accepted: bool = False):
        """注册连接（默认 accept，_already_accepted=True 时跳过）"""
        if not _already_accepted:
            await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(websocket)
        logger.info(f"WebSocket 已连接: channel={channel}, 当前连接数={self.count(channel)}")

    def disconnect(self, websocket: WebSocket, channel: str = "default"):
        """移除连接"""
        if channel in self._connections:
            self._connections[channel].discard(websocket)
            if not self._connections[channel]:
                del self._connections[channel]
        logger.info(f"WebSocket 已断开: channel={channel}, 当前连接数={self.count(channel)}")

    async def send_to(self, websocket: WebSocket, data: dict):
        """发送给单个连接"""
        try:
            await websocket.send_json(data)
        except Exception:
            logger.warning("WebSocket 发送失败，连接可能已断开")

    async def broadcast(self, channel: str, data: dict):
        """广播给某个 channel 的所有连接"""
        connections = self._connections.get(channel, set()).copy()
        disconnected = []
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        # 清理断开的连接
        for ws in disconnected:
            self.disconnect(ws, channel)

    async def broadcast_all(self, data: dict):
        """广播给所有 channel"""
        for channel in list(self._connections.keys()):
            await self.broadcast(channel, data)

    def count(self, channel: str = None) -> int:
        """获取连接数"""
        if channel:
            return len(self._connections.get(channel, set()))
        return sum(len(v) for v in self._connections.values())

    def channels(self) -> list:
        """获取所有 channel 列表"""
        return list(self._connections.keys())


# 全局单例
ws_manager = WebSocketManager()
