/**
 * 聊天 API 服务
 *
 * 对接后端会话（conversation）和消息（message）管理接口。
 * AI 对话接口后端暂未实现，保留 mock 并标注 TODO。
 */

import { apiClient } from '@/services/api-client'
import type {
  ChatRequest,
  ChatResponse,
  FeedbackRequest,
  FeedbackResponse,
  StreamToken,
  Conversation,
  ChatMessage,
} from '../types/chat'

// ── 后端类型 ─────────────────────────────────────────────────

interface BackendConversation {
  id: number
  title: string
  model_name: string
  message_count: number
  last_message_at: string | null
  created_at: string
  updated_at: string
}

interface BackendMessage {
  id: number
  conversation_id: number
  role: string
  content: string
  tool_calls: any
  tool_call_id: string | null
  token_count: number
  created_at: string
  updated_at: string
}

// ── 转换函数 ─────────────────────────────────────────────────

function toFrontendConversation(item: BackendConversation): Conversation {
  return {
    id: String(item.id),
    title: item.title || '新会话',
    createdAt: new Date(item.created_at).getTime(),
    updatedAt: new Date(item.updated_at).getTime(),
    messageCount: item.message_count,
    lastMessage: undefined,
  }
}

function toFrontendMessage(item: BackendMessage): ChatMessage {
  return {
    id: String(item.id),
    conversationId: String(item.conversation_id),
    role: item.role as ChatMessage['role'],
    content: item.content,
    createdAt: new Date(item.created_at).getTime(),
    metadata: item.token_count ? { tokenCount: item.token_count } : undefined,
  }
}

// ── 会话管理 API（真实接口）────────────────────────────────────

/** 获取会话列表 */
export async function fetchConversations(params?: {
  page?: number
  pageSize?: number
}): Promise<{ items: Conversation[]; total: number }> {
  const resp = await apiClient.get('/conversations', {
    params: { page: params?.page ?? 1, page_size: params?.pageSize ?? 50 },
  })
  const body = resp.data as any
  return {
    items: (body.data ?? []).map(toFrontendConversation),
    total: body.total ?? 0,
  }
}

/** 创建会话 */
export async function createConversation(title?: string): Promise<Conversation> {
  const resp = await apiClient.post('/conversations', {
    title: title ?? '新会话',
    model_name: '',
  })
  const raw = (resp.data as any)?.data
  if (!raw || typeof raw.id === 'undefined') {
    throw new Error('创建会话失败：后端返回数据格式异常')
  }
  return toFrontendConversation(raw)
}

/** 更新会话 */
export async function updateConversation(
  id: string,
  data: { title?: string }
): Promise<Conversation> {
  const resp = await apiClient.put(`/conversations/${id}`, data)
  const raw = (resp.data as any)?.data
  if (!raw) throw new Error('更新会话失败：后端返回数据异常')
  return toFrontendConversation(raw)
}

/** 删除会话 */
export async function deleteConversationApi(id: string): Promise<void> {
  await apiClient.delete(`/conversations/${id}`)
}

// ── 消息管理 API（真实接口）────────────────────────────────────

/** 获取会话消息列表 */
export async function fetchMessages(
  conversationId: string,
  params?: { page?: number; pageSize?: number }
): Promise<{ items: ChatMessage[]; total: number }> {
  const resp = await apiClient.get('/messages', {
    params: {
      conversation_id: conversationId,
      page: params?.page ?? 1,
      page_size: params?.pageSize ?? 50,
    },
  })
  const body = resp.data as any
  return {
    items: (body.data ?? []).map(toFrontendMessage),
    total: body.total ?? 0,
  }
}

/** 保存消息到后端 */
export async function saveMessage(
  conversationId: string,
  role: 'user' | 'assistant' | 'system',
  content: string,
  tokenCount?: number
): Promise<ChatMessage> {
  const resp = await apiClient.post('/messages', {
    conversation_id: Number(conversationId),
    role,
    content,
    token_count: tokenCount ?? 0,
  })
  return toFrontendMessage((resp.data as any).data)
}

// ── AI 对话 API（真实接口）────────────────────────────────────

/**
 * 发送非流式聊天请求
 */
export async function chat(request: ChatRequest): Promise<ChatResponse> {
  // 保存用户消息
  await saveMessage(request.conversationId, 'user', request.message)

  // 调用后端对话接口
  const resp = await apiClient.post(
    `/conversations/${request.conversationId}/chat`,
    {
      provider_id: request.providerId,
      model_name: request.modelName ?? '',
      messages: [{ role: 'user', content: request.message }],
      temperature: 0.7,
      max_tokens: 2048,
      stream: false,
    }
  )

  const data = (resp.data as any).data
  return {
    id: crypto.randomUUID(),
    content: data.content ?? '',
    isCached: false,
    model: data.model ?? '',
  }
}

/**
 * 创建流式聊天连接（SSE）
 * 单一端点: POST /conversations/{id}/chat, body 中 stream=true
 */
export function chatStream(
  request: ChatRequest,
  onToken: (token: StreamToken) => void,
  onError?: (error: Error) => void
): { abort: () => void } {
  const controller = new AbortController()
  const messageId = crypto.randomUUID()

  // 保存用户消息（异步，不阻塞）
  saveMessage(request.conversationId, 'user', request.message).catch(() => {})

  const doStream = async (): Promise<void> => {
    try {
      const resp = await fetch(
        `/api/v1/conversations/${request.conversationId}/chat`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider_id: request.providerId,
            model_name: request.modelName ?? '',
            messages: [{ role: 'user', content: request.message }],
            temperature: 0.7,
            max_tokens: 2048,
            stream: true,
          }),
          signal: controller.signal,
        }
      )

      if (!resp.ok) {
        const errText = await resp.text()
        throw new Error(`HTTP ${resp.status}: ${errText}`)
      }

      const reader = resp.body?.getReader()
      if (!reader) throw new Error('No readable stream')

      const decoder = new TextDecoder()
      let buffer = ''
      let firstToken = true

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.error) {
              onError?.(new Error(data.error))
              return
            }
            if (data.content || data.done) {
              onToken({
                content: data.content ?? '',
                done: data.done,
                messageId: firstToken ? messageId : undefined,
              })
              firstToken = false
            }
            if (data.done) return
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError?.(err instanceof Error ? err : new Error(String(err)))
      }
    }
  }

  doStream()

  return {
    abort: () => controller.abort(),
  }
}

/**
 * 提交反馈
 */
export async function submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
  // TODO: 对接后端反馈接口
  console.log('[Feedback]', request)
  return { success: true }
}
