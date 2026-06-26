/**
 * 聊天 API 服务
 *
 * 使用 extractData / extractPaginated 消除 as any。
 * 类型转换仅做 id: number→string 等业务适配。
 *
 * 后端参数名（FastAPI Query/Path 使用 Python 变量名，即 snake_case）：
 *   - GET  /messages?conversation_id=&page=&page_size=
 *   - POST /conversations/{conversation_id}/chat
 *   - POST /messages body: { conversation_id, role, content, token_count }
 *   - POST /conversations body: { title, model_name }
 *
 * 后端 CamelModel 的 populate_by_name=True 同时接受 camelCase 和 snake_case 请求体，
 * 但 Query/Path 参数是 Python 变量名，必须用 snake_case。
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  FeedbackRequest, FeedbackResponse,
  Conversation, ChatMessage,
} from '../types/chat'

// ── 业务适配（id 类型转换）──────────────────────────────────

function adaptConversation(item: any): Conversation {
  return {
    id: String(item.id),
    title: item.title || '新会话',
    modelName: item.modelName ?? '',
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

/** 创建会话
 *  后端 ConversationCreate 字段: title, model_name
 *  CamelModel alias_generator=to_camel + populate_by_name=True → 同时接受 modelName
 */
export async function createConversation(title?: string, modelName?: string): Promise<Conversation> {
  const raw = extractData(await apiClient.post('/conversations', {
    title: title ?? '新会话', model_name: modelName ?? '',
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

/**
 * 获取会话消息列表
 * 后端 Query 参数: conversation_id (必填), page, page_size
 */
export async function fetchMessages(
  conversationId: string, params?: { page?: number; pageSize?: number }
): Promise<{ items: ChatMessage[]; total: number }> {
  const { items, total } = extractPaginated(
    await apiClient.get('/messages', {
      params: {
        conversationId: Number(conversationId),
        page: params?.page ?? 1,
        pageSize: params?.pageSize ?? 50,
      },
    }) as any
  )
  return { items: items.map(adaptMessage), total }
}

/**
 * 保存消息到后端
 * 后端 MessageCreate 字段: conversation_id, role, content, token_count
 * CamelModel alias → 同时接受 conversationId, tokenCount
 */
export async function saveMessage(
  conversationId: string, role: 'user' | 'assistant' | 'system',
  content: string, tokenCount?: number
): Promise<ChatMessage> {
  const raw = extractData(await apiClient.post('/messages', {
    conversationId: Number(conversationId), role, content, token_count: tokenCount ?? 0,
  }))
  return adaptMessage(raw)
}

// ── AI 对话 API ──────────────────────────────────────────────
// chatStreamWS / chatResumeStreamWS 已迁移至 chat-stream-manager.ts

/** 提交反馈 — 调用后端 POST /ai_feedback */
export async function submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
  extractData(await apiClient.post('/ai_feedback', {
    conversationId: request.conversationId ? Number(request.conversationId) : undefined,
    question: request.question ?? '',
    answer: request.answer ?? '',
    feedbackType: request.type === 'positive' ? 0 : 1,
    reasonTags: request.reasons,
    reasonText: request.comment ?? '',
    traceId: crypto.randomUUID(),
  }))
  return { success: true }
}
