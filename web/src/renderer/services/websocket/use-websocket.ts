/**
 * useWebSocket Hook
 *
 * 在组件中使用 WebSocket 功能。
 *
 * @example
 * ```tsx
 * const { send, subscribe, isConnected, connectionState } = useWebSocket();
 *
 * useEffect(() => {
 *   const unsub = subscribe('notification', (msg) => {
 *     console.log('New notification:', msg.payload);
 *   });
 *   return unsub;
 * }, [subscribe]);
 * ```
 */

import { useContext } from 'react'
import { WebSocketContext } from './websocket-provider'

/**
 * 获取 WebSocket 上下文
 * 必须在 WebSocketProvider 内部使用
 */
export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}
