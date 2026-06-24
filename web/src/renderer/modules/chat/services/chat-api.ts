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
import { API_BASE_URL, API_PREFIX } from '@shared/constants'
import type {
  ChatRequest, FeedbackRequest, FeedbackResponse,
  StreamToken, Conversation, ChatMessage, ToolProgress, ApprovalRequest, ContextSource, ProgressStep,
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

/**
 * 创建流式聊天连接（SSE）— 支持审批/工具进度/上下文引用/成本事件
 * 后端路径: POST /conversations/{conversation_id}/chat
 */
export function chatStream(
  request: ChatRequest,
  onToken: (token: StreamToken) => void,
  onError?: (error: Error) => void,
  callbacks?: {
    onToolStart?: (tool: string, args: Record<string, unknown>) => void
    onToolEnd?: (tool: string, outputPreview: string) => void
    onToolError?: (tool: string, outputPreview: string) => void
    onApproval?: (req: ApprovalRequest) => void
    onCostUpdate?: (promptTokens: number, completionTokens: number) => void
    onIntentHit?: (name: string, score: number) => void
    onProgress?: (progress: ProgressStep) => void
    onGoalSubtasks?: (subtasks: Array<{ id: number; title: string; description?: string; status: string }>) => void
  }
): { abort: () => void } {
  const controller = new AbortController()
  const messageId = crypto.randomUUID()

  // 消息保存由后端 save_skill_messages 统一负责，前端不再重复保存

  const doStream = async (): Promise<void> => {
    try {
      const url = `${API_BASE_URL}${API_PREFIX}/conversations/${request.conversationId}/chat`
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Trace-Id': crypto.randomUUID() },
        body: JSON.stringify({
          provider_id: request.providerId, model_name: request.modelName ?? '',
          messages: [{ role: 'user', content: request.message }],
          temperature: 0.7, max_tokens: 2048, stream: true,
          reasoning_depth: request.reasoningDepth ?? 'balanced',
          team_mode: request.teamMode ?? 'off',
          team_id: request.teamId ?? null,
          skill_id: request.skillId ?? null,
          goal_mode: request.goalMode ?? false,
          goal_definition: request.goalMode ? request.message : '',
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

            // 工具开始事件
            if (data.tool_start) {
              callbacks?.onToolStart?.(data.tool_start, data.tool_args ?? {})
              continue
            }
            // 工具结束事件
            if (data.tool_end) {
              callbacks?.onToolEnd?.(data.tool_end, data.output_preview ?? '')
              continue
            }
            // 工具失败事件
            if (data.tool_error) {
              callbacks?.onToolError?.(data.tool_error, data.output_preview ?? '')
              continue
            }
            // 审批事件（v4.2 新增 — interrupt/resume 支持）
            if (data.approval_required) {
              callbacks?.onApproval?.({
                tool: data.approval_required.tool ?? '',
                args: data.approval_required.args ?? {},
                message: data.approval_required.message ?? '',
              })
              continue
            }
            // 成本更新事件
            if (data.cost) {
              callbacks?.onCostUpdate?.(data.cost.prompt_tokens ?? 0, data.cost.completion_tokens ?? 0)
              continue
            }
            // 意图命中事件
            if (data.intent_hit) {
              callbacks?.onIntentHit?.(data.intent_hit, data.intent_score ?? 0)
              continue
            }
            // 进展事件（AG-UI 协议兼容）
            if (data.progress) {
              callbacks?.onProgress?.(data.progress as ProgressStep)
              continue
            }
            // Goal 模式子任务更新事件
            if (data.goal_subtasks) {
              callbacks?.onGoalSubtasks?.(data.goal_subtasks)
              continue
            }
            // token 事件
            if (data.content || data.done) {
              onToken({ content: data.content ?? '', done: data.done, messageId: firstToken ? messageId : undefined })
              firstToken = false
            }
            // thinking 事件
            if (data.thinking) {
              onToken({ content: '', thinking: data.thinking, done: false })
            }
            // done 事件中可能包含 goal_subtasks
            if (data.done && data.goal_subtasks) {
              callbacks?.onGoalSubtasks?.(data.goal_subtasks)
            }
            if (data.done) return
          } catch { /* skip malformed JSON */ }
        }
      }

      // 流正常关闭后，处理 buffer 中可能残留的最后一行（done 事件可能在此）
      if (buffer.trim()) {
        for (const line of buffer.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.content || data.done) {
              onToken({ content: data.content ?? '', done: data.done, messageId: firstToken ? messageId : undefined })
              firstToken = false
            }
            if (data.thinking) {
              onToken({ content: '', thinking: data.thinking, done: false })
            }
            if (data.done) return
          } catch { /* skip malformed JSON */ }
        }
      }

      // 兜底：流正常关闭但未收到 done 事件 → 强制结束加载状态
      onToken({ content: '', done: true, messageId: undefined })
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError?.(err instanceof Error ? err : new Error(String(err)))
      }
    }
  }

  const done = doStream()
  return { abort: () => controller.abort(), done }
}

/**
 * 审批恢复 — 流式 SSE（LangGraph interrupt/resume 官方模式）
 *
 * 后端路径: POST /conversations/{conversation_id}/chat/resume
 * 流程: 前端发送审批决定 → 后端 Command(resume=...) 恢复 Agent → 流式返回后续执行
 */
export function chatResumeStream(
  conversationId: string,
  request: { approved: boolean; toolName?: string; toolArgs?: Record<string, unknown>; userResponse?: string },
  onToken: (token: StreamToken) => void,
  onError?: (error: Error) => void,
  callbacks?: {
    onToolStart?: (tool: string, args: Record<string, unknown>) => void
    onToolEnd?: (tool: string, outputPreview: string) => void
  }
): { abort: () => void } {
  const controller = new AbortController()
  const messageId = crypto.randomUUID()

  const doStream = async (): Promise<void> => {
    try {
      const url = `${API_BASE_URL}${API_PREFIX}/conversations/${conversationId}/chat/resume`
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Trace-Id': crypto.randomUUID() },
        body: JSON.stringify({
          approved: request.approved,
          tool_name: request.toolName ?? '',
          tool_args: request.toolArgs ?? null,
          user_response: request.userResponse ?? '',
          stream: true,
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

            if (data.tool_start) {
              callbacks?.onToolStart?.(data.tool_start, data.tool_args ?? {})
              continue
            }
            if (data.tool_end) {
              callbacks?.onToolEnd?.(data.tool_end, data.output_preview ?? '')
              continue
            }
            if (data.content || data.done) {
              onToken({ content: data.content ?? '', done: data.done, messageId: firstToken ? messageId : undefined })
              firstToken = false
            }
            if (data.thinking) {
              onToken({ content: '', thinking: data.thinking, done: false })
            }
            if (data.done) return
          } catch { /* skip malformed JSON */ }
        }
      }

      // 流正常关闭后，处理 buffer 中可能残留的最后一行
      if (buffer.trim()) {
        for (const line of buffer.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.content || data.done) {
              onToken({ content: data.content ?? '', done: data.done, messageId: firstToken ? messageId : undefined })
              firstToken = false
            }
            if (data.thinking) {
              onToken({ content: '', thinking: data.thinking, done: false })
            }
            if (data.done) return
          } catch { /* skip malformed JSON */ }
        }
      }

      // 兜底：流正常关闭但未收到 done 事件
      onToken({ content: '', done: true, messageId: undefined })
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError?.(err instanceof Error ? err : new Error(String(err)))
      }
    }
  }

  const done = doStream()
  return { abort: () => controller.abort(), done }
}

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
