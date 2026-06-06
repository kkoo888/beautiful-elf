/**
 * WebSocket 服务导出
 */

export { WebSocketClient } from './websocket-client'
export { WebSocketContext, WebSocketProvider } from './websocket-provider'
export { useWebSocket, useWSMessage, useConnectionState, useSendMessage } from './use-websocket'
export { MessageQueue } from './message-queue'
export { EventDeduplicator } from './types'
export type {
  WSMessage,
  WSMessageType,
  ConnectionState,
  MessageHandler,
  Unsubscribe,
  WebSocketConfig,
  QueuedMessage,
} from './types'
