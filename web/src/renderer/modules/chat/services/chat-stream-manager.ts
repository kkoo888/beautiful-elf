/**
 * Chat 流式请求管理器
 *
 * 在 chatWSClient（/ws/chat 持久连接）之上封装请求路由。
 * 复用 WebSocketClient 的连接管理（重连/心跳/离线队列），
 * 单一 pending 策略：聊天是串行的，同一时间只有一个活跃流。
 */

import { chatWSClient } from '@/services/websocket'
import type {
  ChatRequest,
  StreamToken,
  ApprovalRequest,
  ProgressStep,
} from '../types/chat'

/** 回调集合 */
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

/** 待处理请求 */
interface PendingRequest {
  onToken: (token: StreamToken) => void
  onError?: (error: Error) => void
  callbacks?: ChatStreamCallbacks
  resolveDone: () => void
  timeout?: ReturnType<typeof setTimeout>
}

/** 审批恢复请求 */
export interface ResumeRequest {
  conversationId: string
  approved: boolean
  toolName?: string
  toolArgs?: Record<string, unknown>
  userResponse?: string
}

class ChatStreamManager {
  private currentPending: PendingRequest | null = null
  private initialized = false

  constructor() {
    this.init()
  }

  private init() {
    if (this.initialized) return
    this.initialized = true

    // 订阅 chat_* 事件，直接路由到当前 pending（串行，无需 requestId）
    chatWSClient.subscribe('*', (msg: any) => {
      if (!this.currentPending) return

      // 后端发扁平格式：{type: "chat_token", content: "..."}
      // WebSocketClient 解析为 WSMessage，但后端没有 payload 字段
      // 所以字段在 msg 本身（扁平）或 msg.payload（信封）里
      const type: string = msg.type ?? ''
      if (!type.startsWith('chat_') && type !== 'chat_start') return

      this.dispatch(type, msg, this.currentPending)
    })
  }

  /** 确保已连接，返回 Promise 在连接就绪时 resolve */
  private ensureConnected(): Promise<void> {
    return new Promise((resolve) => {
      if (chatWSClient.getConnectionState() === 'connected') {
        resolve()
        return
      }
      chatWSClient.connect()
      const unsub = chatWSClient.onStateChange((state) => {
        if (state === 'connected') {
          unsub()
          resolve()
        }
      })
    })
  }

  /** 普通对话 */
  sendChat(
    request: ChatRequest,
    onToken: (token: StreamToken) => void,
    onError?: (error: Error) => void,
    callbacks?: ChatStreamCallbacks,
  ): { abort: () => void; done: Promise<void> } {
    this.ensureConnected()

    let resolveDone!: () => void
    const done = new Promise<void>((r) => { resolveDone = r })

    // 超时保护：30s 无事件视为失败
    const timeout = setTimeout(() => {
      if (this.currentPending) {
        this.currentPending.onError?.(new Error('连接超时，请重试'))
        this.currentPending.resolveDone()
        this.currentPending = null
      }
    }, 30_000)

    this.currentPending = { onToken, onError, callbacks, resolveDone, timeout }

    // 异步等待连接就绪后发送
    this.sendRaw({
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
    }).catch((err) => {
      console.error('[ChatStreamManager] sendRaw failed:', err)
      if (this.currentPending) {
        this.currentPending.onError?.(err)
        this.currentPending.resolveDone()
        this.currentPending = null
      }
    })

    return {
      abort: () => {
        if (this.currentPending) {
          clearTimeout(this.currentPending.timeout)
          this.currentPending = null
        }
      },
      done,
    }
  }

  /** 审批恢复 — 走 WS 而非 SSE */
  resumeChat(
    request: ResumeRequest,
    onToken: (token: StreamToken) => void,
    onError?: (error: Error) => void,
    callbacks?: Pick<ChatStreamCallbacks, 'onToolStart' | 'onToolEnd' | 'onToolError'>,
  ): { abort: () => void; done: Promise<void> } {
    this.ensureConnected()

    let resolveDone!: () => void
    const done = new Promise<void>((r) => { resolveDone = r })

    const timeout = setTimeout(() => {
      if (this.currentPending) {
        this.currentPending.onError?.(new Error('连接超时，请重试'))
        this.currentPending.resolveDone()
        this.currentPending = null
      }
    }, 30_000)

    this.currentPending = { onToken, onError, callbacks, resolveDone, timeout }

    this.sendRaw({
      type: 'resume',
      conversationId: request.conversationId,
      approved: request.approved,
      toolName: request.toolName ?? '',
      toolArgs: request.toolArgs ?? null,
      userResponse: request.userResponse ?? '',
    }).catch((err) => {
      console.error('[ChatStreamManager] sendRaw failed:', err)
      if (this.currentPending) {
        this.currentPending.onError?.(err)
        this.currentPending.resolveDone()
        this.currentPending = null
      }
    })

    return {
      abort: () => {
        if (this.currentPending) {
          clearTimeout(this.currentPending.timeout)
          this.currentPending = null
        }
      },
      done,
    }
  }

  /** 直接发扁平 JSON，等连接就绪后再发 */
  private async sendRaw(data: Record<string, unknown>) {
    await this.ensureConnected()
    chatWSClient.sendRaw(data)
  }

  /** 按事件类型分发到当前 pending request */
  private dispatch(type: string, raw: any, pending: PendingRequest) {
    // 收到任何事件都重置超时
    if (pending.timeout) {
      clearTimeout(pending.timeout)
      pending.timeout = undefined
    }

    // 后端扁平格式：字段在顶层
    const data = raw

    switch (type) {
      case 'chat_start':
        break

      case 'chat_token':
        pending.onToken({ content: (data.content as string) ?? '', done: false })
        break

      case 'chat_thinking':
        pending.onToken({ content: '', thinking: (data.content as string) ?? '', done: false })
        break

      case 'chat_tool_start':
        pending.callbacks?.onToolStart?.(
          (data.tool as string) ?? '',
          (data.args as Record<string, unknown>) ?? {},
        )
        break

      case 'chat_tool_end':
        pending.callbacks?.onToolEnd?.(
          (data.tool as string) ?? '',
          (data.output_preview as string) ?? '',
        )
        break

      case 'chat_tool_error':
        pending.callbacks?.onToolError?.(
          (data.tool as string) ?? '',
          (data.output_preview as string) ?? '',
        )
        break

      case 'chat_progress':
        pending.callbacks?.onProgress?.(data as unknown as ProgressStep)
        break

      case 'chat_goal_subtasks':
        pending.callbacks?.onGoalSubtasks?.(
          (data.subtasks as Array<{ id: number; title: string; description?: string; status: string }>) ?? [],
        )
        break

      case 'chat_goal_tool_update':
        pending.callbacks?.onGoalToolUpdate?.(data as any)
        break

      case 'chat_intent_hit':
        pending.callbacks?.onIntentHit?.(
          (data.intent as string) ?? '',
          (data.score as number) ?? 0,
        )
        break

      case 'chat_cost_update':
        pending.callbacks?.onCostUpdate?.(
          (data.prompt_tokens as number) ?? 0,
          (data.completion_tokens as number) ?? 0,
        )
        break

      case 'chat_approval_required':
        pending.callbacks?.onApproval?.({
          tool: (data.tool as string) ?? '',
          args: (data.args as Record<string, unknown>) ?? {},
          message: (data.message as string) ?? '',
        })
        break

      case 'chat_done':
        pending.onToken({
          content: '',
          done: true,
          toolsUsed: data.tools_used as string[],
          durationMs: data.duration_ms as number,
          promptTokens: data.prompt_tokens as number,
          completionTokens: data.completion_tokens as number,
          goalSubtasks: data.goal_subtasks as any,
        })
        pending.resolveDone()
        this.currentPending = null
        break

      case 'chat_error':
        pending.onError?.(new Error((data.message as string) ?? '未知错误'))
        pending.resolveDone()
        this.currentPending = null
        break
    }
  }
}

export const chatStreamManager = new ChatStreamManager()
