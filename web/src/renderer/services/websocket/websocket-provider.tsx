/**
 * WebSocket React Context Provider
 *
 * 将 WebSocketClient 包装为 React Context，供整个应用使用。
 */

import { createContext, useEffect, useRef, useState, useCallback, useMemo } from 'react'
import type { ReactNode } from 'react'
import { WebSocketClient } from './websocket-client'
import type {
  WSMessage,
  WSMessageType,
  ConnectionState,
  MessageHandler,
  Unsubscribe,
  WebSocketConfig,
} from './types'

interface WebSocketContextValue {
  /** 发送消息 */
  send: (message: WSMessage) => void
  /** 订阅指定类型消息，返回取消订阅函数 */
  subscribe: (type: WSMessageType | '*', handler: MessageHandler) => Unsubscribe
  /** 当前是否已连接 */
  isConnected: boolean
  /** 当前连接状态 */
  connectionState: ConnectionState
}

export const WebSocketContext = createContext<WebSocketContextValue | null>(null)

interface WebSocketProviderProps {
  config?: Partial<WebSocketConfig>
  children: ReactNode
}

/**
 * WebSocket Provider 组件
 *
 * @example
 * ```tsx
 * <WebSocketProvider config={{ url: 'ws://localhost:8080/ws' }}>
 *   <App />
 * </WebSocketProvider>
 * ```
 */
export function WebSocketProvider({ config, children }: WebSocketProviderProps) {
  const clientRef = useRef<WebSocketClient | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')

  // 初始化客户端
  if (!clientRef.current) {
    clientRef.current = new WebSocketClient(config)
  }

  useEffect(() => {
    const client = clientRef.current!
    let mounted = true

    // 初始化消息队列
    client.initQueue().then(() => {
      if (mounted) {
        client.connect()
      }
    })

    // 监听连接状态
    const unsub = client.onStateChange((state) => {
      if (mounted) {
        setConnectionState(state)
      }
    })

    return () => {
      mounted = false
      unsub()
      client.destroy()
      clientRef.current = null
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const send = useCallback((message: WSMessage) => {
    clientRef.current?.send(message)
  }, [])

  const subscribe = useCallback((type: WSMessageType | '*', handler: MessageHandler): Unsubscribe => {
    return clientRef.current?.subscribe(type, handler) ?? (() => {})
  }, [])

  const value = useMemo<WebSocketContextValue>(
    () => ({
      send,
      subscribe,
      isConnected: connectionState === 'connected',
      connectionState,
    }),
    [send, subscribe, connectionState],
  )

  return <WebSocketContext value={value}>{children}</WebSocketContext>
}
