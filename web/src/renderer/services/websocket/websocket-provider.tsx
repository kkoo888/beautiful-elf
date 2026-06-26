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
  closeReason,
  onReconnect,
}: {
  connectionState: ConnectionState
  closeReason: 'auth_expired' | 'auth_invalid' | null
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
  const isAuthError = closeReason === 'auth_expired' || closeReason === 'auth_invalid'

  const authMessage = closeReason === 'auth_expired'
    ? '登录已过期，请重新登录'
    : '登录凭证无效，请重新登录'

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
        type={isAuthError ? 'error' : (isConnecting ? 'warning' : 'error')}
        showIcon
        icon={isConnecting ? <ReloadOutlined spin /> : <DisconnectOutlined />}
        title={
          isAuthError ? authMessage : (
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
          )
        }
        description={
          isAuthError ? (
            <Space>
              <Button size="small" type="primary" onClick={() => { window.location.href = '/login' }}>
                重新登录
              </Button>
              <Button size="small" type="text" onClick={() => setDismissed(true)}>
                ✕
              </Button>
            </Space>
          ) : undefined
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
  const [closeReason, setCloseReason] = useState<'auth_expired' | 'auth_invalid' | null>(null)

  // 稳定化 config 引用，避免重复初始化
  const stableConfig = useMemo(() => config, [config?.url])

  useEffect(() => {
    // 在 useEffect 内部初始化，避免竞态
    const client = new WebSocketClient(stableConfig)
    clientRef.current = client
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
        // 连接恢复时清除关闭原因
        if (state === 'connected') {
          setCloseReason(null)
        }
      }
    })

    // 监听关闭原因
    const unsubReason = client.onCloseReason((reason) => {
      if (mounted) {
        setCloseReason(reason)
      }
    })

    // 监听 chat WS 的 auth 错误（chat 模块使用独立 WS 连接）
    const handleChatAuthError = (e: Event) => {
      const code = (e as CustomEvent).detail?.code
      if (mounted && (code === 4001 || code === 4003)) {
        setCloseReason(code === 4001 ? 'auth_expired' : 'auth_invalid')
        setConnectionState('disconnected')
      }
    }
    window.addEventListener('ws-auth-error', handleChatAuthError)

    return () => {
      mounted = false
      unsub()
      unsubReason()
      window.removeEventListener('ws-auth-error', handleChatAuthError)
      client.destroy()
      clientRef.current = null
    }
  }, [stableConfig])

  const send = useCallback((message: WSMessage) => {
    clientRef.current?.send(message)
  }, [])

  const subscribe = useCallback(
    (type: WSMessageType | '*', handler: MessageHandler): Unsubscribe => {
      return clientRef.current?.subscribe(type, handler) ?? (() => {})
    },
    []
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
    [send, subscribe, connectionState]
  )

  return (
    <WebSocketContext value={value}>
      {showDisconnectBanner && (
        <DisconnectBanner connectionState={connectionState} closeReason={closeReason} onReconnect={handleReconnect} />
      )}
      {children}
    </WebSocketContext>
  )
}
