/**
 * WebSocket 客户端核心类
 *
 * 功能：
 * 1. 自动连接、断线检测、指数退避重连
 * 2. 心跳检测（30s ping/pong）
 * 3. 离线消息队列（IndexedDB）
 * 4. 事件分发（按 type 分发 handler）
 * 5. event_id LRU 去重缓存
 */

import type {
  WSMessage,
  WSMessageType,
  ConnectionState,
  MessageHandler,
  Unsubscribe,
  WebSocketConfig,
} from './types'
import { MessageQueue } from './message-queue'

const DEFAULT_CONFIG: Required<WebSocketConfig> = {
  url: 'ws://localhost:8080/ws',
  heartbeatInterval: 30_000,
  heartbeatTimeout: 3,
  reconnectInitialDelay: 1_000,
  reconnectMaxDelay: 30_000,
  reconnectJitter: 0.5,
  dedupeCacheSize: 100,
}

export class WebSocketClient {
  private config: Required<WebSocketConfig>
  private ws: WebSocket | null = null
  private connectionState: ConnectionState = 'disconnected'
  private handlers = new Map<WSMessageType | '*', Set<MessageHandler>>()
  private messageQueue: MessageQueue

  // 心跳
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private missedPongs = 0

  // 重连
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts = 0
  private manualClose = false

  // event_id 去重 LRU 缓存
  private eventIdCache: string[] = []
  private eventIdSet = new Set<string>()

  // 连接状态变更回调
  private stateListeners = new Set<(state: ConnectionState) => void>()

  constructor(config?: Partial<WebSocketConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config }
    this.messageQueue = new MessageQueue()
  }

  // ─── 公开 API ─────────────────────────────────

  /** 建立 WebSocket 连接 */
  connect(): void {
    if (this.connectionState === 'connected' || this.connectionState === 'connecting') {
      return
    }

    this.manualClose = false
    this.setConnectionState('connecting')

    try {
      this.ws = new WebSocket(this.config.url)
      this.ws.onopen = this.handleOpen.bind(this)
      this.ws.onmessage = this.handleMessage.bind(this)
      this.ws.onclose = this.handleClose.bind(this)
      this.ws.onerror = this.handleError.bind(this)
    } catch {
      this.setConnectionState('disconnected')
      this.scheduleReconnect()
    }
  }

  /** 主动断开连接 */
  disconnect(): void {
    this.manualClose = true
    this.stopHeartbeat()
    this.clearReconnectTimer()

    if (this.ws) {
      this.setConnectionState('disconnecting')
      this.ws.close(1000, 'Manual close')
      this.ws = null
    }

    this.setConnectionState('disconnected')
  }

  /** 发送消息（断网时自动入队） */
  send(message: WSMessage): void {
    if (this.connectionState === 'connected' && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      // 断网时存入 IndexedDB 队列
      this.messageQueue.enqueue(message).catch(console.error)
    }
  }

  /** 订阅指定类型消息 */
  subscribe(type: WSMessageType | '*', handler: MessageHandler): Unsubscribe {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler)

    return () => {
      this.handlers.get(type)?.delete(handler)
    }
  }

  /** 监听连接状态变更 */
  onStateChange(listener: (state: ConnectionState) => void): Unsubscribe {
    this.stateListeners.add(listener)
    return () => {
      this.stateListeners.delete(listener)
    }
  }

  /** 获取当前连接状态 */
  getConnectionState(): ConnectionState {
    return this.connectionState
  }

  /** 初始化消息队列（需要在使用前调用） */
  async initQueue(): Promise<void> {
    await this.messageQueue.init()
  }

  /** 销毁客户端，释放所有资源 */
  destroy(): void {
    this.disconnect()
    this.handlers.clear()
    this.stateListeners.clear()
    this.eventIdCache = []
    this.eventIdSet.clear()
    this.messageQueue.close()
  }

  // ─── 内部方法 ─────────────────────────────────

  /** WebSocket 连接成功 */
  private handleOpen(): void {
    this.setConnectionState('connected')
    this.reconnectAttempts = 0
    this.missedPongs = 0
    this.startHeartbeat()
    this.flushQueue()
  }

  /** 收到 WebSocket 消息 */
  private handleMessage(event: MessageEvent): void {
    let message: WSMessage

    try {
      message = JSON.parse(event.data) as WSMessage
    } catch {
      console.warn('[WebSocket] Invalid message format:', event.data)
      return
    }

    // 处理 pong 响应
    if (message.type === 'pong') {
      this.missedPongs = 0
      return
    }

    // 忽略客户端发出的 ping
    if (message.type === 'ping') return

    // event_id 去重
    if (message.event_id && this.isDuplicate(message.event_id)) {
      return
    }

    // 分发到对应 handler
    this.dispatch(message)
  }

  /** WebSocket 连接关闭 */
  private handleClose(event: CloseEvent): void {
    this.stopHeartbeat()
    this.ws = null

    if (this.manualClose) {
      this.setConnectionState('disconnected')
      return
    }

    this.setConnectionState('disconnected')
    console.warn(`[WebSocket] Connection closed: code=${event.code}, reason=${event.reason}`)
    this.scheduleReconnect()
  }

  /** WebSocket 错误 */
  private handleError(): void {
    console.error('[WebSocket] Connection error')
    // onerror 后通常会触发 onclose，由 onclose 处理重连
  }

  // ─── 心跳 ─────────────────────────────────

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.missedPongs = 0

    this.heartbeatTimer = setInterval(() => {
      if (this.missedPongs >= this.config.heartbeatTimeout) {
        console.warn('[WebSocket] Heartbeat timeout, reconnecting...')
        this.ws?.close(4000, 'Heartbeat timeout')
        return
      }

      this.missedPongs++
      this.send({
        type: 'ping',
        payload: {},
        timestamp: Date.now(),
      })
    }, this.config.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  // ─── 重连 ─────────────────────────────────

  private scheduleReconnect(): void {
    if (this.manualClose) return
    this.clearReconnectTimer()

    // 指数退避 + 抖动
    const base = this.config.reconnectInitialDelay * Math.pow(2, this.reconnectAttempts)
    const delay = Math.min(base, this.config.reconnectMaxDelay)
    const jitter = delay * this.config.reconnectJitter * Math.random()
    const finalDelay = delay + jitter

    console.log(
      `[WebSocket] Reconnecting in ${Math.round(finalDelay)}ms (attempt ${this.reconnectAttempts + 1})`
    )

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, finalDelay)
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  // ─── 消息队列 ─────────────────────────────────

  /** 网络恢复后发送排队消息 */
  private async flushQueue(): Promise<void> {
    try {
      const messages = await this.messageQueue.dequeueAll()

      for (const queued of messages) {
        if (this.connectionState !== 'connected') break

        try {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(queued.message))
            await this.messageQueue.remove(queued.id)
          }
        } catch {
          await this.messageQueue.incrementRetry(queued.id)
        }
      }
    } catch (err) {
      console.error('[WebSocket] Failed to flush message queue:', err)
    }
  }

  // ─── event_id 去重 ─────────────────────────────

  private isDuplicate(eventId: string): boolean {
    if (this.eventIdSet.has(eventId)) {
      return true
    }

    // 添加到 LRU 缓存
    this.eventIdCache.push(eventId)
    this.eventIdSet.add(eventId)

    // 超出容量时淘汰最旧的
    while (this.eventIdCache.length > this.config.dedupeCacheSize) {
      const oldest = this.eventIdCache.shift()!
      this.eventIdSet.delete(oldest)
    }

    return false
  }

  // ─── 事件分发 ─────────────────────────────────

  private dispatch(message: WSMessage): void {
    // 分发到类型匹配的 handler
    const typeHandlers = this.handlers.get(message.type)
    if (typeHandlers) {
      for (const handler of typeHandlers) {
        try {
          handler(message)
        } catch (err) {
          console.error(`[WebSocket] Handler error for type "${message.type}":`, err)
        }
      }
    }

    // 分发到通配符 handler
    const wildcardHandlers = this.handlers.get('*')
    if (wildcardHandlers) {
      for (const handler of wildcardHandlers) {
        try {
          handler(message)
        } catch (err) {
          console.error('[WebSocket] Wildcard handler error:', err)
        }
      }
    }
  }

  // ─── 状态管理 ─────────────────────────────────

  private setConnectionState(state: ConnectionState): void {
    if (this.connectionState === state) return
    this.connectionState = state

    for (const listener of this.stateListeners) {
      try {
        listener(state)
      } catch (err) {
        console.error('[WebSocket] State listener error:', err)
      }
    }
  }
}
