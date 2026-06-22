/**
 * WebSocket 消息与状态类型定义
 */

/** WebSocket 连接状态 */
export type ConnectionState = 'connecting' | 'connected' | 'disconnecting' | 'disconnected'

/** WebSocket 消息类型 */
export type WSMessageType =
  | 'config_update'
  | 'notification'
  | 'pet_state'
  | 'workflow_progress'
  | 'subagent_status'
  | 'ai_chunk'
  | 'expert_status'
  | 'expert_thinking'
  | 'expert_progress'
  | 'distill_complete'
  | 'distill_error'
  | 'ping'
  | 'pong'

/** WebSocket 消息格式 */
export interface WSMessage {
  type: WSMessageType
  payload: Record<string, unknown>
  timestamp: number
  eventId?: string
}

/** 消息处理器 */
export type MessageHandler = (message: WSMessage) => void

/** 订阅取消函数 */
export type Unsubscribe = () => void

/** WebSocket 客户端配置 */
export interface WebSocketConfig {
  /** WebSocket 服务地址 */
  url: string
  /** 心跳间隔（ms），默认 30000 */
  heartbeatInterval?: number
  /** 连续未收到 pong 次数判定断线，默认 3 */
  heartbeatTimeout?: number
  /** 重连初始延迟（ms），默认 1000 */
  reconnectInitialDelay?: number
  /** 重连最大延迟（ms），默认 30000 */
  reconnectMaxDelay?: number
  /** 重连抖动系数，默认 0.5 */
  reconnectJitter?: number
  /** event_id 去重缓存大小，默认 100 */
  dedupeCacheSize?: number
}

/** IndexedDB 离线消息 */
export interface QueuedMessage {
  id: string
  message: WSMessage
  createdAt: number
  retryCount: number
}

/**
 * event_id LRU 去重缓存
 * 用于防止重复事件被多次处理
 */
export class EventDeduplicator {
  private cache = new Map<string, number>()
  private readonly maxSize: number

  constructor(maxSize = 100) {
    this.maxSize = maxSize
  }

  /** 检查是否为重复事件 */
  isDuplicate(eventId: string): boolean {
    return this.cache.has(eventId)
  }

  /** 记录事件，超出容量时淘汰最旧的 */
  add(eventId: string): void {
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value
      if (firstKey) this.cache.delete(firstKey)
    }
    this.cache.set(eventId, Date.now())
  }

  /** 检查并添加（原子操作），返回 true 表示是重复的 */
  checkAndAdd(eventId: string): boolean {
    if (this.isDuplicate(eventId)) return true
    this.add(eventId)
    return false
  }

  /** 清空缓存 */
  clear(): void {
    this.cache.clear()
  }

  /** 当前缓存大小 */
  get size(): number {
    return this.cache.size
  }
}
