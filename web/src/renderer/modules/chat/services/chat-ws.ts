/**
 * Chat WebSocket — 一个持久连接，所有消息走它
 *
 * 打开页面 → 建立连接 → 所有消息复用 → 30 分钟无活动断开
 * 不依赖 WebSocketClient（避免自动重连冲突）
 */

import { API_BASE_URL } from '@shared/constants'
import type {
  ChatRequest,
  StreamToken,
  ApprovalRequest,
  ProgressStep,
} from '../types/chat'

export interface ChatStreamCallbacks {
  onToolStart?: (tool: string, args: Record<string, unknown>) => void
  onToolEnd?: (tool: string, outputPreview: string) => void
  onToolError?: (tool: string, outputPreview: string) => void
  onApproval?: (req: ApprovalRequest) => void
  onCostUpdate?: (promptTokens: number, completionTokens: number) => void
  onIntentHit?: (name: string, score: number) => void
  onProgress?: (progress: ProgressStep) => void
  onGoalSubtasks?: (subtasks: Array<{ id: number; title: string; description?: string; status: string }>) => void
  onGoalToolUpdate?: (update: { task_id: number; tool: string; tool_status: string; args?: Record<string, unknown>; output_preview?: string }) => void
}

// ── 单一持久连接 ──────────────────────────────────

let ws: WebSocket | null = null
let connected = false
let connectPromise: Promise<void> | null = null

function getWsUrl(): string {
  return API_BASE_URL.replace(/^http/, 'ws') + `/api/v1/ws/chat?token=${localStorage.getItem('beautiful-elf:auth_token') || ''}`
}

/** 获取或建立连接，返回已连接的 WebSocket */
function ensureConnected(): Promise<WebSocket> {
  if (ws && connected && ws.readyState === WebSocket.OPEN) {
    return Promise.resolve(ws)
  }
  if (connectPromise) return connectPromise.then(() => ws!)

  connectPromise = new Promise<WebSocket>((resolve, reject) => {
    const socket = new WebSocket(getWsUrl())

    socket.onopen = () => {
      connected = true
      connectPromise = null
      ws = socket
      resolve(socket)
    }

    socket.onclose = () => {
      connected = false
      ws = null
      connectPromise = null
    }

    socket.onerror = () => {
      connected = false
      connectPromise = null
      reject(new Error('WebSocket 连接失败'))
    }
  })

  return connectPromise.then(() => ws!)
}

/** 发送扁平 JSON */
function send(data: Record<string, unknown>) {
  if (ws && connected && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data))
  }
}

// ── 普通对话 ──────────────────────────────────────

export function chatStream(
  request: ChatRequest,
  onToken: (token: StreamToken) => void,
  onError?: (error: Error) => void,
  callbacks?: ChatStreamCallbacks,
): { abort: () => void; done: Promise<void> } {
  let aborted = false
  let completed = false
  let firstToken = true
  let resolveDone!: () => void
  const done = new Promise<void>((r) => { resolveDone = r })

  // token 节流 16ms
  let throttleTimer: ReturnType<typeof setTimeout> | null = null
  let pendingContent = ''
  let pendingThinking = ''
  const flushThrottle = () => {
    throttleTimer = null
    const c = pendingContent
    const t = pendingThinking
    pendingContent = ''
    pendingThinking = ''
    if (c || t) onToken({ content: c, thinking: t || undefined, done: false })
  }

  // 30s 无事件超时
  let inactivityTimer: ReturnType<typeof setTimeout> | null = null
  const resetInactivity = () => {
    if (inactivityTimer) clearTimeout(inactivityTimer)
    inactivityTimer = setTimeout(() => {
      if (!aborted && !completed) {
        onError?.(new Error('连接超时，请重试'))
        completed = true
        resolveDone()
      }
    }, 180_000)
  }

  // 消息分发
  const handleMessage = (event: MessageEvent) => {
    if (aborted || completed) return
    resetInactivity()
    try {
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'ping':
          send({ type: 'pong' })
          break
        case 'chat_start':
          break
        case 'chat_token':
          pendingContent += data.content ?? ''
          if (!throttleTimer) throttleTimer = setTimeout(flushThrottle, 16)
          if (firstToken) { onToken({ content: '', done: false }); firstToken = false }
          break
        case 'chat_thinking':
          pendingThinking += data.content ?? ''
          if (!throttleTimer) throttleTimer = setTimeout(flushThrottle, 16)
          break
        case 'chat_tool_start':
          callbacks?.onToolStart?.(data.tool, data.args ?? {})
          break
        case 'chat_tool_end':
          callbacks?.onToolEnd?.(data.tool, data.output_preview ?? '')
          break
        case 'chat_tool_error':
          callbacks?.onToolError?.(data.tool, data.output_preview ?? '')
          break
        case 'chat_progress':
          callbacks?.onProgress?.(data as ProgressStep)
          break
        case 'chat_goal_subtasks':
          callbacks?.onGoalSubtasks?.(data.subtasks)
          break
        case 'chat_goal_tool_update':
          callbacks?.onGoalToolUpdate?.(data)
          break
        case 'chat_intent_hit':
          callbacks?.onIntentHit?.(data.intent, data.score ?? 0)
          break
        case 'chat_cost_update':
          callbacks?.onCostUpdate?.(data.prompt_tokens ?? 0, data.completion_tokens ?? 0)
          break
        case 'chat_approval_required':
          callbacks?.onApproval?.({ tool: data.tool ?? '', args: data.args ?? {}, message: data.message ?? '' })
          break
        case 'chat_done':
          if (data.goal_subtasks) callbacks?.onGoalSubtasks?.(data.goal_subtasks)
          // 先 flush 残留 token，再 cleanup
          if (throttleTimer) { clearTimeout(throttleTimer); throttleTimer = null }
          flushThrottle()
          if (inactivityTimer) { clearTimeout(inactivityTimer); inactivityTimer = null }
          if (ws) ws.removeEventListener('message', handleMessage)
          completed = true
          onToken({ content: '', done: true, toolsUsed: data.tools_used, durationMs: data.duration_ms, promptTokens: data.prompt_tokens, completionTokens: data.completion_tokens, goalSubtasks: data.goal_subtasks })
          resolveDone()
          break
        case 'chat_error':
          if (throttleTimer) { clearTimeout(throttleTimer); throttleTimer = null }
          flushThrottle()
          if (inactivityTimer) { clearTimeout(inactivityTimer); inactivityTimer = null }
          if (ws) ws.removeEventListener('message', handleMessage)
          completed = true
          onError?.(new Error(data.message))
          resolveDone()
          break
      }
    } catch { /* skip malformed */ }
  }

  const cleanup = () => {
    if (throttleTimer) { clearTimeout(throttleTimer); throttleTimer = null }
    if (inactivityTimer) { clearTimeout(inactivityTimer); inactivityTimer = null }
    if (ws) {
      ws.removeEventListener('message', handleMessage)
      // 不关闭连接 — 保持持久，下次复用
    }
  }

  // 确保连接就绪后发送
  ensureConnected().then((socket) => {
    if (aborted || completed) return
    ws = socket
    socket.addEventListener('message', handleMessage)
    resetInactivity()
    send({
      type: 'chat',
      content: request.message,
      conversationId: request.conversationId,
      providerId: request.providerId,
      modelName: request.modelName ?? '',
      reasoningDepth: request.reasoningDepth ?? 'balanced',
      goalMode: request.goalMode ?? false,
      goalDefinition: request.goalMode ? request.message : '',
      teamMode: request.teamMode ?? 'off',
      teamId: request.teamId ?? null,
      skillId: request.skillId ?? null,
      temperature: 0.7,
      maxTokens: 4096,
    })
  }).catch((err) => {
    if (!completed) {
      onError?.(err)
      completed = true
      resolveDone()
    }
  })

  return {
    abort: () => {
      aborted = true
      cleanup()
      resolveDone()
    },
    done,
  }
}

// ── 审批恢复 ──────────────────────────────────────

export function chatResumeStream(
  conversationId: string,
  request: { approved: boolean; toolName?: string; toolArgs?: Record<string, unknown>; userResponse?: string },
  onToken: (token: StreamToken) => void,
  onError?: (error: Error) => void,
  callbacks?: Pick<ChatStreamCallbacks, 'onToolStart' | 'onToolEnd' | 'onToolError'>,
): { abort: () => void; done: Promise<void> } {
  let aborted = false
  let completed = false
  let firstToken = true
  let resolveDone!: () => void
  const done = new Promise<void>((r) => { resolveDone = r })

  let inactivityTimer: ReturnType<typeof setTimeout> | null = null
  const resetInactivity = () => {
    if (inactivityTimer) clearTimeout(inactivityTimer)
    inactivityTimer = setTimeout(() => {
      if (!aborted && !completed) {
        onError?.(new Error('连接超时，请重试'))
        completed = true
        resolveDone()
      }
    }, 180_000)
  }

  const handleMessage = (event: MessageEvent) => {
    if (aborted || completed) return
    resetInactivity()
    try {
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'ping':
          send({ type: 'pong' })
          break
        case 'chat_token':
          onToken({ content: data.content ?? '', done: false, messageId: firstToken ? 'resume' : undefined })
          firstToken = false
          break
        case 'chat_thinking':
          onToken({ content: '', thinking: data.content ?? '', done: false })
          break
        case 'chat_tool_start':
          callbacks?.onToolStart?.(data.tool, data.args ?? {})
          break
        case 'chat_tool_end':
          callbacks?.onToolEnd?.(data.tool, data.output_preview ?? '')
          break
        case 'chat_tool_error':
          callbacks?.onToolError?.(data.tool, data.output_preview ?? '')
          break
        case 'chat_done':
          cleanup()
          completed = true
          onToken({ content: '', done: true, toolsUsed: data.tools_used, durationMs: data.duration_ms, promptTokens: data.prompt_tokens, completionTokens: data.completion_tokens, goalSubtasks: data.goal_subtasks })
          resolveDone()
          break
        case 'chat_error':
          cleanup()
          completed = true
          onError?.(new Error(data.message))
          resolveDone()
          break
      }
    } catch { /* skip malformed */ }
  }

  const cleanup = () => {
    if (inactivityTimer) { clearTimeout(inactivityTimer); inactivityTimer = null }
    if (ws) ws.removeEventListener('message', handleMessage)
  }

  ensureConnected().then((socket) => {
    if (aborted || completed) return
    ws = socket
    socket.addEventListener('message', handleMessage)
    resetInactivity()
    send({
      type: 'resume',
      conversationId,
      approved: request.approved,
      toolName: request.toolName ?? '',
      toolArgs: request.toolArgs ?? null,
      userResponse: request.userResponse ?? '',
    })
  }).catch((err) => {
    if (!completed) {
      onError?.(err)
      completed = true
      resolveDone()
    }
  })

  return {
    abort: () => {
      aborted = true
      cleanup()
      resolveDone()
    },
    done,
  }
}
