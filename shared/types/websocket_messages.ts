/**
 * WebSocket 消息类型 - 前后端共享
 */

/** WS 消息基础格式 */
export interface WSMessage<T = unknown> {
  type: string
  channel?: string
  data: T
  timestamp?: string
}

/** 聊天消息 */
export interface WSChatMessage {
  type: 'message' | 'typing' | 'error'
  conversation_id: number
  content: string
  role: 'user' | 'assistant'
}

/** 通知推送 */
export interface WSNotification {
  type: 'notification'
  id: number
  title: string
  message: string
  notification_type: string
}

/** 宠物状态更新 */
export interface WSPetUpdate {
  type: 'pet_update'
  attributes: {
    hunger: number
    clean: number
    mood: number
    health: number
    intimacy: number
    level: number
    exp: number
  }
}

/** 系统事件 */
export interface WSSystemEvent {
  type: 'system_event'
  event: string
  payload: unknown
}
