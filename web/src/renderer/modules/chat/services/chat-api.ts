/**
 * 聊天 API 服务
 *
 * 使用 extractData / extractPaginated 消除 as any。
 * 类型转换仅做 id: number→string 等业务适配。
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse,
  StreamToken, Conversation, ChatMessage,
} from '../types/chat'

// ── 业务适配（id 类型转换）──────────────────────────────────

function adaptConversation(item: any): Conversation {
  return {
    id: String(item.id),
    title: item.title || '新会话',
    createdAt: new Date(item.createdAt).getTime(),
    updatedAt: new Date(item.updatedAt).getTime(),
    messageCount: item.messageCount ?? 0,
    lastMessage: undefined,
  }
}

function adaptMessage(item: any): ChatMessage {
  return {
    id: String(item.id),
    conversationId: String(item.conversationId),
    role: item.role as ChatMessage['role'],
    content: item.content,
    createdAt: new Date(item.createdAt).getTime(),
    metadata: item.tokenCount ? { tokenCount: item.tokenCount } : undefined,
  }
}

// ── 会话管理 API ─────────────────────────────────────────────

/** 获取会话列表 */
export async function fetchConversations(params?: {
  page?: number; pageSize?: number
}): Promise<{ items: Conversation[]; total: number }> {
  const { items, total } = extractPaginated(
    await apiClient.get('/conversations', {
      params: { page: params?.page ?? 1, pageSize: params?.pageSize ?? 50 },
    }) as any
  )
  return { items: items.map(adaptConversation), total }
}

/** 创建会话 */
export async function createConversation(title?: string): Promise<Conversation> {
  const raw = extractData(await apiClient.post('/conversations', {
    title: title ?? '新会话', modelName: '',
  }))
  if (!raw) throw new Error('创建会话失败：后端返回数据为空')
  return adaptConversation(raw)
}

/** 更新会话 */
export async function updateConversation(id: string, data: { title?: string }): Promise<Conversation> {
  const raw = extractData(await apiClient.put(`/conversations/${id}`, data))
  if (!raw) throw new Error('更新会话失败：后端返回数据异常')
  return adaptConversation(raw)
}

/** 删除会话 */
export async function deleteConversationApi(id: string): Promise<void> {
  await apiClient.delete(`/conversations/${id}`)
}

// ── 消息管理 API ─────────────────────────────────────────────

/** 获取会话消息列表 */
export async function fetchMessages(
  conversationId: string, params?: { page?: number; pageSize?: number }
): Promise<{ items: ChatMessage[]; total: number }> {
  const { items, total } = extractPaginated(
    await apiClient.get('/messages', {
      params: { conversationId, page: params?.page ?? 1, pageSize: params?.pageSize ?? 50 },
    }) as any
  )
  return { items: items.map(adaptMessage), total }
}

/** 保存消息到后端 */
export async function saveMessage(
  conversationId: string, role: 'user' | 'assistant' | 'system',
  content: string, tokenCount?: number
): Promise<ChatMessage> {
  const raw = extractData(await apiClient.post('/messages', {
    conversationId: Number(conversationId), role, content, tokenCount: tokenCount ?? 0,
  }))
  return adaptMessage(raw)
}

// ── AI 对话 API ──────────────────────────────────────────────

/** 发送非流式聊天请求 */
export async function chat(request: ChatRequest): Promise<ChatResponse> {
  await saveMessage(request.conversationId, 'user', request.message)
  const data = extractData(await apiClient.post(`/conversations/${request.conversationId}/chat`, {
    providerId: request.providerId, modelName: request.modelName ?? '',
    messages: [{ role: 'user', content: request.message }],
    temperature: 0.7, maxTokens: 2048, stream: false,
  })) as any
  return {
    id: crypto.randomUUID(), content: data.content ?? '',
    isCached: false, model: data.model ?? '',
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

  saveMessage(request.conversationId, 'user', request.message).catch(() => {})

  const doStream = async (): Promise<void> => {
    try {
      const resp = await fetch(`/api/v1/conversations/${request.conversationId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Trace-Id': crypto.randomUUID() },
        body: JSON.stringify({
          providerId: request.providerId, modelName: request.modelName ?? '',
          messages: [{ role: 'user', content: request.message }],
          temperature: 0.7, maxTokens: 2048, stream: true,
        }),
        signal: controller.signal,
      })

      if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`)

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
            if (data.error) { onError?.(new Error(data.error)); return }
            if (data.content || data.done) {
              onToken({ content: data.content ?? '', done: data.done, messageId: firstToken ? messageId : undefined })
              firstToken = false
            }
            if (data.done) return
          } catch { /* skip malformed JSON */ }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError?.(err instanceof Error ? err : new Error(String(err)))
      }
    }
  }

  doStream()
  return { abort: () => controller.abort() }
}

/** 提交反馈 */
export async function submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
  // TODO: 对接后端反馈接口
  console.log('[Feedback]', request)
  return { success: true }
}
