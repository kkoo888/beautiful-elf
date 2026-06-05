/** 聊天模块类型定义 */

/** 消息角色 */
export type MessageRole = 'user' | 'assistant' | 'system'

/** 推理深度 */
export type ReasoningDepth = 'fast' | 'deep' | 'full'

/** 反馈类型 */
export type FeedbackType = 'positive' | 'negative'

/** 反馈原因标签 */
export type FeedbackReason =
  | 'inaccurate'
  | 'irrelevant'
  | 'harmful'
  | 'outdated'
  | 'unclear'
  | 'other'

/** 意图路由信息 */
export interface IntentRoute {
  /** 匹配到的模块名 */
  module: string
  /** 置信度 0-1 */
  confidence: number
}

/** 消息元数据 */
export interface MessageMetadata {
  /** 是否为语义缓存命中（快速回答） */
  isCached?: boolean
  /** 意图路由信息 */
  intentRoute?: IntentRoute
  /** 模型名称 */
  model?: string
  /** token 消耗 */
  tokenCount?: number
}

/** 反馈数据 */
export interface FeedbackData {
  /** 消息 ID */
  messageId: string
  /** 反馈类型 */
  type: FeedbackType
  /** 负面反馈原因 */
  reasons?: FeedbackReason[]
  /** 补充说明 */
  comment?: string
}

/** 聊天消息 */
export interface ChatMessage {
  /** 消息唯一 ID */
  id: string
  /** 所属会话 ID */
  conversationId: string
  /** 消息角色 */
  role: MessageRole
  /** 消息内容 */
  content: string
  /** 创建时间戳 */
  createdAt: number
  /** 元数据 */
  metadata?: MessageMetadata
  /** 用户反馈 */
  feedback?: FeedbackData
}

/** 会话 */
export interface Conversation {
  /** 会话 ID */
  id: string
  /** 会话标题 */
  title: string
  /** 创建时间 */
  createdAt: number
  /** 更新时间 */
  updatedAt: number
  /** 消息数量 */
  messageCount: number
  /** 最后一条消息预览 */
  lastMessage?: string
}

/** 聊天请求 */
export interface ChatRequest {
  /** 会话 ID */
  conversationId: string
  /** 用户消息 */
  message: string
  /** 推理深度 */
  reasoningDepth: ReasoningDepth
  /** 供应商 ID */
  providerId?: number
  /** 供应商类型（后端需要） */
  providerType?: string
  /** 模型名称 */
  modelName?: string
}

/** 聊天响应 */
export interface ChatResponse {
  /** 消息 ID */
  id: string
  /** 消息内容 */
  content: string
  /** 是否为缓存回答 */
  isCached: boolean
  /** 意图路由 */
  intentRoute?: IntentRoute
  /** 模型名称 */
  model: string
}

/** 流式 token */
export interface StreamToken {
  /** token 内容 */
  content: string
  /** 是否为最后一个 token */
  done: boolean
  /** 消息 ID（首个 token 返回） */
  messageId?: string
}

/** 反馈提交请求 */
export interface FeedbackRequest {
  /** 消息 ID */
  messageId: string
  /** 反馈类型 */
  type: FeedbackType
  /** 原因标签 */
  reasons?: FeedbackReason[]
  /** 补充说明 */
  comment?: string
  /** 用户问题（后端必填，由调用方从消息链回溯） */
  question?: string
  /** AI 回答（后端必填，由调用方从消息链回溯） */
  answer?: string
  /** 会话 ID */
  conversationId?: string
}

/** 反馈提交响应 */
export interface FeedbackResponse {
  success: boolean
}

/** WebSocket 事件类型 */
export type WSEventType = 'stream_start' | 'stream_token' | 'stream_end' | 'error'

/** WebSocket 事件 */
export interface WSEvent {
  type: WSEventType
  payload: StreamToken | { error: string }
  timestamp: number
}
