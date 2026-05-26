import { useEffect, useRef, useCallback, useState } from 'react'
import { WS_URL, WS_HEARTBEAT_INTERVAL, WS_RECONNECT_INITIAL, WS_RECONNECT_MAX } from '@shared/constants'

type WSStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

interface WSMessage {
  type: string
  payload: unknown
  timestamp: number
  event_id: string
}

interface UseWebSocketOptions {
  onMessage?: (message: WSMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  autoConnect?: boolean
}

/**
 * WebSocket 连接管理 Hook
 * 包含心跳检测、指数退避重连、event_id 去重
 */
export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onMessage, onConnect, onDisconnect, autoConnect = true } = options

  const wsRef = useRef<WebSocket | null>(null)
  const heartbeatTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  const eventIdCache = useRef<Set<string>>(new Set())

  const [status, setStatus] = useState<WSStatus>('disconnected')

  // 清理定时器
  const clearTimers = useCallback(() => {
    if (heartbeatTimer.current) {
      clearInterval(heartbeatTimer.current)
      heartbeatTimer.current = null
    }
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }
  }, [])

  // 开始心跳
  const startHeartbeat = useCallback(() => {
    clearTimers()
    heartbeatTimer.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, WS_HEARTBEAT_INTERVAL)
  }, [clearTimers])

  // 计算重连延迟（指数退避 + 抖动）
  const getReconnectDelay = useCallback(() => {
    const delay = Math.min(WS_RECONNECT_INITIAL * Math.pow(2, reconnectAttempts.current), WS_RECONNECT_MAX)
    const jitter = delay * 0.5 * Math.random()
    return delay + jitter
  }, [])

  // 连接
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setStatus('connecting')
    const ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      setStatus('connected')
      reconnectAttempts.current = 0
      startHeartbeat()
      onConnect?.()
    }

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)

        // event_id 去重
        if (message.event_id) {
          if (eventIdCache.current.has(message.event_id)) return
          eventIdCache.current.add(message.event_id)
          // 保持缓存大小
          if (eventIdCache.current.size > 100) {
            const first = eventIdCache.current.values().next().value
            if (first) eventIdCache.current.delete(first)
          }
        }

        onMessage?.(message)
      } catch {
        console.error('[WS] Failed to parse message')
      }
    }

    ws.onclose = () => {
      setStatus('disconnected')
      clearTimers()
      onDisconnect?.()

      // 自动重连
      setStatus('reconnecting')
      const delay = getReconnectDelay()
      reconnectTimer.current = setTimeout(() => {
        reconnectAttempts.current++
        connect()
      }, delay)
    }

    ws.onerror = () => {
      ws.close()
    }

    wsRef.current = ws
  }, [onMessage, onConnect, onDisconnect, startHeartbeat, clearTimers, getReconnectDelay])

  // 断开连接
  const disconnect = useCallback(() => {
    clearTimers()
    reconnectAttempts.current = 0
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus('disconnected')
  }, [clearTimers])

  // 发送消息
  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  // 自动连接
  useEffect(() => {
    if (autoConnect) {
      connect()
    }
    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  return {
    status,
    isConnected: status === 'connected',
    connect,
    disconnect,
    send
  }
}
