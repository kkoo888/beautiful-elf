/**
 * WebSocket React Context Provider
 *
 * 将 WebSocketClient 包装为 React Context，供整个应用使用。
 * 包含断线提示条功能。
 */

import { createContext, useEffect, useRef, useState, useCallback, useMemo } from 'react'
import type { ReactNode } from 'react'
import { Alert, Button, Space } from 'antd'
import { DisconnectOutlined, ReloadOutlined } from '@ant-design/icons'
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
  /** 是否显示断线提示条，默认 true */
  showDisconnectBanner?: boolean
}

/**
 * 断线提示条组件
 */
function DisconnectBanner({
  connectionState,
  onReconnect,
}: {
  connectionState: ConnectionState
  onReconnect: () => void
}) {
  const [dismissed, setDismissed] = useState(false)

  // 连接恢复时重置 dismissed
  useEffect(() => {
    if (connectionState === 'connected') {
      setDismissed(false)
    }
  }, [connectionState])

  if (dismissed) return null
  if (connectionState === 'connected' || connectionState === 'disconnecting') return null

  const isConnecting = connectionState === 'connecting'

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        padding: '4px 16px',
      }}
    >
      <Alert
        type={isConnecting ? 'warning' : 'error'}
        showIcon
        icon={isConnecting ? <ReloadOutlined spin /> : <DisconnectOutlined />}
        message={
          <Space>
            <span>
              {isConnecting ? '正在重新连接服务器...' : '与服务器断开连接，部分功能可能不可用'}
            </span>
            {!isConnecting && (
              <Button size="small" type="link" onClick={onReconnect}>
                立即重连
              </Button>
            )}
            <Button size="small" type="text" onClick={() => setDismissed(true)}>
              ✕
            </Button>
          </Space>
        }
        banner
      />
    </div>
  )
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
export function WebSocketProvider({
  config,
  children,
  showDisconnectBanner = true,
}: WebSocketProviderProps) {
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

  const subscribe = useCallback(
    (type: WSMessageType | '*', handler: MessageHandler): Unsubscribe => {
      return clientRef.current?.subscribe(type, handler) ?? (() => {})
    },
    [],
  )

  const handleReconnect = useCallback(() => {
    const client = clientRef.current
    if (client) {
      // 先断开再重连，清除旧状态
      client.disconnect()
      setTimeout(() => client.connect(), 100)
    }
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

  return (
    <WebSocketContext value={value}>
      {showDisconnectBanner && (
        <DisconnectBanner
          connectionState={connectionState}
          onReconnect={handleReconnect}
        />
      )}
      {children}
    </WebSocketContext>
  )
}
