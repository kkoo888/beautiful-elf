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
  return toFrontendConversation((resp.data as any).data)
}

/** 更新会话 */
export async function updateConversation(
  id: string,
  data: { title?: string }
): Promise<Conversation> {
  const resp = await apiClient.put(`/conversations/${id}`, data)
  return toFrontendConversation((resp.data as any).data)
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
  const resp = await apiClient.get(`/conversations/${conversationId}/messages`, {
    params: {
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
  const resp = await apiClient.post(`/conversations/${conversationId}/messages`, {
    role,
    content,
    token_count: tokenCount ?? 0,
  })
  return toFrontendMessage((resp.data as any).data)
}

// ── AI 对话 API（mock，后端暂未实现）────────────────────────────

/** 模拟延迟 */
const delay = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

/** Mock 响应内容池 */
const MOCK_RESPONSES: string[] = [
  '你好！有什么可以帮你的吗？ 😊',
  '这是一个很好的问题！让我来帮你分析一下。\n\n**关键点：**\n1. 首先需要理解需求\n2. 然后拆解任务\n3. 最后逐步实现',
  '根据我的理解，这里有几个方案：\n\n- **方案 A**：简单直接\n- **方案 B**：更灵活但复杂\n- **方案 C**：平衡方案\n\n推荐方案 C，兼顾了简洁和灵活性。',
  '```typescript\nfunction greet(name: string): string {\n  return `Hello, ${name}!`\n}\n\nconsole.log(greet("Beautiful-Elf"))\n```\n\n这段代码展示了基本的 TypeScript 函数定义。',
  '让我想想... 🤔\n\n这个问题涉及到几个方面：\n\n> 设计原则：单一职责、开闭原则、依赖倒置\n\n建议先从最简单的实现开始，逐步迭代优化。',
]

const MOCK_MODULES = ['schedule', 'clipboard', 'knowledge', 'translate', 'skills']

/**
 * 发送非流式聊天请求（Mock）
 * TODO: 对接后端 AI 对话接口（需后端新增 /chat 端点）
 */
export async function chat(request: ChatRequest): Promise<ChatResponse> {
  await delay(800 + Math.random() * 1200)

  // 保存用户消息到后端
  try {
    await saveMessage(request.conversationId, 'user', request.message)
  } catch {
    // 忽略保存失败
  }

  const responseIndex = Math.floor(Math.random() * MOCK_RESPONSES.length)
  const isCached = Math.random() > 0.7
  const intentRoute =
    Math.random() > 0.6
      ? {
          module: MOCK_MODULES[Math.floor(Math.random() * MOCK_MODULES.length)],
          confidence: 0.7 + Math.random() * 0.3,
        }
      : undefined

  const content = MOCK_RESPONSES[responseIndex]

  // 保存 AI 回复到后端
  try {
    await saveMessage(request.conversationId, 'assistant', content)
  } catch {
    // 忽略保存失败
  }

  return {
    id: crypto.randomUUID(),
    content,
    isCached,
    intentRoute,
    model: 'qwen2.5:7b',
  }
}

/**
 * 创建流式聊天连接（Mock）
 * TODO: 对接后端流式接口（SSE 或 WebSocket）
 */
export function chatStream(
  request: ChatRequest,
  onToken: (token: StreamToken) => void,
  onError?: (error: Error) => void
): { abort: () => void } {
  let aborted = false
  const messageId = crypto.randomUUID()
  const responseIndex = Math.floor(Math.random() * MOCK_RESPONSES.length)
  const fullContent = MOCK_RESPONSES[responseIndex]
  const chars = [...fullContent]

  // 保存用户消息
  saveMessage(request.conversationId, 'user', request.message).catch(() => {})

  const stream = async (): Promise<void> => {
    try {
      await delay(300)

      for (let i = 0; i < chars.length; i++) {
        if (aborted) break

        onToken({
          content: chars[i],
          done: false,
          messageId: i === 0 ? messageId : undefined,
        })

        await delay(20 + Math.random() * 40)
      }

      if (!aborted) {
        onToken({
          content: '',
          done: true,
          messageId: undefined,
        })

        // 保存完整 AI 回复
        saveMessage(request.conversationId, 'assistant', fullContent).catch(() => {})
      }
    } catch (err) {
      if (!aborted && onError) {
        onError(err instanceof Error ? err : new Error(String(err)))
      }
    }
  }

  stream()

  return {
    abort: () => {
      aborted = true
    },
  }
}

/**
 * 提交反馈（Mock）
 * TODO: 对接后端反馈接口（可复用 ai-feedback 模块）
 */
export async function submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
  await delay(300 + Math.random() * 500)
  console.log('[Mock] Feedback submitted:', request)
  return { success: true }
}
