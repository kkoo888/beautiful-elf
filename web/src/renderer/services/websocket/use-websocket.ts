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

import { useContext, useEffect, useRef, useCallback, useState } from 'react'
import { WebSocketContext } from './websocket-provider'
import type { WSMessage, WSMessageType, Unsubscribe, MessageHandler } from './types'
import { EventDeduplicator } from './types'

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

/**
 * 订阅指定类型消息，自动去重（基于 event_id）
 * 组件卸载时自动取消订阅
 *
 * @param type 消息类型
 * @param handler 消息处理器
 * @param dedupeSize 去重缓存大小，默认 100
 *
 * @example
 * ```tsx
 * useWSMessage('notification', (msg) => {
 *   notification.info({ message: msg.payload.title as string });
 * });
 * ```
 */
export function useWSMessage(
  type: WSMessageType | '*',
  handler: MessageHandler,
  dedupeSize = 100
): void {
  const { subscribe } = useWebSocket()
  const handlerRef = useRef(handler)
  const dedupRef = useRef<EventDeduplicator | null>(null)

  // 保持 handler 引用最新
  handlerRef.current = handler

  // 初始化去重器（只创建一次）
  if (!dedupRef.current) {
    dedupRef.current = new EventDeduplicator(dedupeSize)
  }

  useEffect(() => {
    const dedup = dedupRef.current!
    const wrappedHandler: MessageHandler = (message: WSMessage) => {
      // event_id 去重
      if (message.event_id && dedup.checkAndAdd(message.event_id)) {
        return
      }
      handlerRef.current(message)
    }

    const unsub = subscribe(type, wrappedHandler)
    return unsub
  }, [type, subscribe])
}

/**
 * 获取当前连接状态
 *
 * @example
 * ```tsx
 * const state = useConnectionState();
 * if (state === 'disconnected') showReconnectBanner();
 * ```
 */
export function useConnectionState() {
  const { connectionState } = useWebSocket()
  return connectionState
}

/**
 * 获取便捷的消息发送函数，自动附加 timestamp 和 event_id
 *
 * @example
 * ```tsx
 * const sendMessage = useSendMessage();
 * sendMessage('config_update', { key: 'theme', value: 'dark' });
 * ```
 */
export function useSendMessage() {
  const { send } = useWebSocket()

  return useCallback(
    (type: WSMessageType, payload: Record<string, unknown>) => {
      const message: WSMessage = {
        type,
        payload,
        timestamp: Date.now(),
        event_id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      }
      send(message)
    },
    [send]
  )
}
