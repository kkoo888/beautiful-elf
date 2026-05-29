/**
 * API 契约 - 前后端共享类型
 * 与后端 schemas/response.py 保持同步
 */

/** 统一 API 响应格式 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  user_tip?: string
  data: T
  request_id?: string
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 分页请求参数 */
export interface PaginationParams {
  page?: number
  page_size?: number
}

/** 会话 */
export interface Conversation {
  id: number
  title: string
  model_name: string
  message_count: number
  last_message_at: string | null
  created_at: string
  updated_at: string
}

/** 消息 */
export interface ChatMessage {
  id: number
  conversation_id: number
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  tool_calls: unknown[] | null
  tool_call_id: string | null
  token_count: number
  created_at: string
}

/** 日程 */
export interface Schedule {
  id: number
  title: string
  description: string
  start_time: string
  end_time: string | null
  all_day: number
  reminder_minutes: number
  reminded: number
  repeat_type: number
  color: string
  created_at: string
}

/** 通知 */
export interface Notification {
  id: number
  event_id: string
  type: string
  title: string
  message: string
  read: number
  action_url: string
  created_at: string
}
