/**
 * 聊天状态管理 Hook
 * 基于 useChatStore，提供聊天操作方法
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useChatStore } from '@/stores/use-chat-store'
import { chat, chatStream, chatResumeStream, submitFeedback, createConversation, fetchMessages, fetchConversations } from '../services/chat-api'
import { getEnabledProviders } from '@/modules/settings/services/settings-api'
import type {
  ChatMessage,
  Conversation,
  FeedbackData,
  ReasoningDepth,
  StreamToken,
  ToolProgress,
  ApprovalRequest,
  ContextSource,
} from '../types/chat'

/** 生成唯一 ID */
const generateId = (): string => crypto.randomUUID()

export interface UseChatReturn {
  /** 消息列表 */
  messages: ChatMessage[]
  /** 当前会话 ID */
  conversationId: string | null
  /** 推理深度 */
  reasoningDepth: ReasoningDepth
  /** 是否正在生成 */
  isLoading: boolean
  /** 会话列表 */
  conversations: Conversation[]
  /** 当前会话 ID（用于会话管理） */
  currentConversationId: string | null
  /** 选中的供应商 ID */
  selectedProviderId: number | undefined
  /** 选中的模型名称 */
  selectedModelName: string | undefined
  /** 工具执行进度列表 */
  toolProgress: ToolProgress[]
  /** 审批请求 */
  approvalRequest: ApprovalRequest | null
  /** 上下文引用来源 */
  contextSources: ContextSource[]
  /** token 统计 */
  tokenStats: { promptTokens: number; completionTokens: number } | null
  /** 发送消息（流式） */
  sendMessage: (content: string) => void
  /** 发送消息（非流式） */
  sendMessageSync: (content: string) => Promise<void>
  /** 设置推理深度 */
  setReasoningDepth: (depth: ReasoningDepth) => void
  /** 设置模型选择 */
  setModelSelection: (providerId: number, modelName: string) => void
  /** 提交反馈 */
  submitFeedback: (data: FeedbackData) => Promise<void>
  /** 清空消息 */
  clearMessages: () => void
  /** 停止生成 */
  stopGeneration: () => void
  /** 创建新会话（调后端 API） */
  createConversation: () => Promise<void>
  /** 切换会话 */
  switchConversation: (id: string) => void
  /** 删除会话 */
  deleteConversation: (id: string) => void
  /** 响应审批 */
  respondApproval: (approved: boolean) => void
}

export function useChat(): UseChatReturn {
  const {
    messages,
    currentConversationId,
    reasoningDepth,
    isLoading,
    conversations,
    selectedProviderId,
    selectedModelName,
    addMessage,
    setMessages,
    setReasoningDepth: storeSetReasoningDepth,
    setModelSelection,
    setIsLoading,
    clearMessages: storeClearMessages,
  } = useChatStore()

  const abortRef = useRef<{ abort: () => void } | null>(null)

  // 新增状态：工具进度、审批、上下文引用、token 统计
  const [toolProgress, setToolProgress] = useState<ToolProgress[]>([])
  const [approvalRequest, setApprovalRequest] = useState<ApprovalRequest | null>(null)
  const [contextSources, setContextSources] = useState<ContextSource[]>([])
  const [tokenStats, setTokenStats] = useState<{ promptTokens: number; completionTokens: number } | null>(null)

  // 缓存 providerId -> providerType 映射，避免每次请求都拉 Provider 列表
  const providerTypeCacheRef = useRef<Record<number, string | undefined>>({})
  // 标记「正在创建会话」，跳过 useEffect 中的 fetchMessages 避免冲掉新消息
  const creatingConvRef = useRef(false)

  // ── 初始化：加载会话列表 ──────────────────────────────
  useEffect(() => {
    fetchConversations().then(({ items }) => {
      useChatStore.getState().setConversations(items)
    }).catch(() => { /* 忽略 */ })
  }, [])

  // ── 切换会话时加载消息 ────────────────────────────────
  useEffect(() => {
    if (!currentConversationId) {
      setMessages([])
      return
    }
    // 如果是 sendMessage 刚创建的会话，跳过 fetch，避免冲掉本地消息
    if (creatingConvRef.current) {
      creatingConvRef.current = false
      return
    }
    fetchMessages(currentConversationId).then(({ items }) => {
      setMessages(items)
    }).catch(() => { /* 忽略 */ })
  }, [currentConversationId])

  const getProviderType = useCallback(async (pid?: number): Promise<string | undefined> => {
    if (!pid) return undefined
    const cache = providerTypeCacheRef.current
    if (cache[pid] !== undefined) return cache[pid]
    try {
      const list = await getEnabledProviders()
      for (const p of list) {
        cache[p.id] = p.providerType
      }
      return cache[pid]
    } catch (err) {
      return undefined
    }
  }, [])

  /** 确保有会话 ID（调用后端创建） */
  const ensureConversationId = useCallback(async (): Promise<string> => {
    if (currentConversationId) return currentConversationId
    const store = useChatStore.getState()
    creatingConvRef.current = true
    const conv = await createConversation('新会话', store.selectedModelName)
    if (!conv) throw new Error('createConversation returned undefined')
    store.addConversation(conv)
    store.setCurrentConversation(conv.id)
    return conv.id
  }, [currentConversationId])

  /** 发送消息（流式） */
  const sendMessage = useCallback(
    async (content: string) => {
      if (isLoading || !content.trim()) return

      const convId = await ensureConversationId()

      // 添加用户消息
      const userMessage: ChatMessage = {
        id: generateId(),
        conversationId: convId,
        role: 'user',
        content: content.trim(),
        createdAt: Date.now(),
      }
      addMessage(userMessage)

      // 更新会话
      useChatStore.getState().updateConversation(convId, {
        updatedAt: Date.now(),
        lastMessage: content.trim(),
        messageCount:
          (useChatStore.getState().conversations.find((c) => c.id === convId)?.messageCount ?? 0) +
          1,
      })

      // 创建 AI 占位消息
      const aiMessageId = generateId()
      const aiMessage: ChatMessage = {
        id: aiMessageId,
        conversationId: convId,
        role: 'assistant',
        content: '',
        createdAt: Date.now(),
      }
      addMessage(aiMessage)
      setIsLoading(true)

      // 流式接收
      const providerType = await getProviderType(selectedProviderId)

      // 重置本轮状态
      setToolProgress([])
      setContextSources([])
      setTokenStats(null)

      abortRef.current = chatStream(
        {
          conversationId: convId,
          message: content.trim(),
          reasoningDepth,
          providerId: selectedProviderId,
          providerType,
          modelName: selectedModelName,
        },
        (token: StreamToken) => {
          if (token.done) {
            setIsLoading(false)
            abortRef.current = null
            // 更新会话最后消息
            const finalMessages = useChatStore.getState().messages
            const lastAiMsg = [...finalMessages].reverse().find((m) => m.role === 'assistant')
            if (lastAiMsg) {
              useChatStore.getState().updateConversation(convId, {
                lastMessage: lastAiMsg.content.slice(0, 100),
                messageCount:
                  (useChatStore.getState().conversations.find((c) => c.id === convId)
                    ?.messageCount ?? 0) + 1,
              })
            }
            return
          }

          // 更新 AI 消息内容（追加 token）
          const currentMessages = useChatStore.getState().messages
          const updatedMessages = currentMessages.map((msg) =>
            msg.id === aiMessageId ? { ...msg, content: msg.content + token.content } : msg
          )
          setMessages(updatedMessages)
        },
        (error) => {
          console.error('[Chat] Stream error:', error)
          const currentMessages = useChatStore.getState().messages
          const updatedMessages = currentMessages.map((msg) =>
            msg.id === aiMessageId
              ? { ...msg, content: msg.content + '\n\n⚠️ 生成中断，请重试' }
              : msg
          )
          setMessages(updatedMessages)
          setIsLoading(false)
          abortRef.current = null
        },
        {
          onToolStart: (tool, args) => {
            setToolProgress((prev) => [...prev, { tool, status: 'running', args, startTime: Date.now() }])
          },
          onToolEnd: (tool, outputPreview) => {
            setToolProgress((prev) =>
              prev.map((t) => t.tool === tool && t.status === 'running' ? { ...t, status: 'done', outputPreview } : t)
            )
          },
          onApproval: (req) => {
            setApprovalRequest(req)
            setIsLoading(false)
          },
          onCostUpdate: (promptTokens, completionTokens) => {
            setTokenStats({ promptTokens, completionTokens })
          },
          onIntentHit: (name, score) => {
            setContextSources((prev) => [...prev, { type: 'intent', name, score }])
          },
        }
      )
    },
    [isLoading, reasoningDepth, selectedProviderId, selectedModelName, ensureConversationId, addMessage, setMessages, setIsLoading]
  )

  /** 发送消息（非流式） */
  const sendMessageSync = useCallback(
    async (content: string): Promise<void> => {
      if (isLoading || !content.trim()) return

      const convId = await ensureConversationId()

      // 添加用户消息
      const userMessage: ChatMessage = {
        id: generateId(),
        conversationId: convId,
        role: 'user',
        content: content.trim(),
        createdAt: Date.now(),
      }
      addMessage(userMessage)

      // 更新会话
      useChatStore.getState().updateConversation(convId, {
        updatedAt: Date.now(),
        lastMessage: content.trim(),
        messageCount:
          (useChatStore.getState().conversations.find((c) => c.id === convId)?.messageCount ?? 0) +
          1,
      })

      setIsLoading(true)

      try {
        const providerType = await getProviderType(selectedProviderId)
        const response = await chat({
          conversationId: convId,
          message: content.trim(),
          reasoningDepth,
          providerId: selectedProviderId,
          providerType,
          modelName: selectedModelName,
        })

        const aiMessage: ChatMessage = {
          id: response.id,
          conversationId: convId,
          role: 'assistant',
          content: response.content,
          createdAt: Date.now(),
          metadata: {
            isCached: response.isCached,
            intentRoute: response.intentRoute,
            model: response.model,
          },
        }
        addMessage(aiMessage)

        // 更新会话
        useChatStore.getState().updateConversation(convId, {
          lastMessage: response.content.slice(0, 100),
          messageCount:
            (useChatStore.getState().conversations.find((c) => c.id === convId)?.messageCount ??
              0) + 1,
        })
      } catch (error) {
        console.error('[Chat] Request error:', error)
        const errorMessage: ChatMessage = {
          id: generateId(),
          conversationId: convId,
          role: 'assistant',
          content: '⚠️ 请求失败，请检查网络后重试',
          createdAt: Date.now(),
        }
        addMessage(errorMessage)
      } finally {
        setIsLoading(false)
      }
    },
    [isLoading, reasoningDepth, selectedProviderId, selectedModelName, ensureConversationId, addMessage, setIsLoading]
  )

  /** 设置推理深度 */
  const setReasoningDepth = useCallback(
    (depth: ReasoningDepth) => {
      storeSetReasoningDepth(depth)
    },
    [storeSetReasoningDepth]
  )

  /** 提交反馈 */
  const handleFeedback = useCallback(
    async (data: FeedbackData): Promise<void> => {
      try {
        // 从消息链回溯 question（用户消息）和 answer（AI 回复）
        const currentMessages = useChatStore.getState().messages
        const answerIdx = currentMessages.findIndex((m) => m.id === data.messageId)
        const answer = answerIdx >= 0 ? currentMessages[answerIdx].content : ''
        let question = ''
        if (answerIdx > 0) {
          // 向前找最近一条 user 消息
          for (let i = answerIdx - 1; i >= 0; i--) {
            if (currentMessages[i].role === 'user') {
              question = currentMessages[i].content
              break
            }
          }
        }

        await submitFeedback({
          messageId: data.messageId,
          type: data.type,
          reasons: data.reasons,
          comment: data.comment,
          question,
          answer,
          conversationId: currentConversationId ?? undefined,
        })

        // 更新本地消息的反馈状态
        const updatedMessages = currentMessages.map((msg) =>
          msg.id === data.messageId ? { ...msg, feedback: data } : msg
        )
        setMessages(updatedMessages)
      } catch (error) {
        console.error('[Chat] Feedback error:', error)
      }
    },
    [setMessages, currentConversationId]
  )

  /** 清空消息 */
  const clearMessages = useCallback(() => {
    storeClearMessages()
    abortRef.current?.abort()
    abortRef.current = null
    setIsLoading(false)
  }, [storeClearMessages, setIsLoading])

  /** 停止生成 */
  const stopGeneration = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setIsLoading(false)
  }, [setIsLoading])

  /** 创建新会话（调后端 API） */
  const handleCreateConversation = useCallback(async () => {
    const store = useChatStore.getState()
    const conv = await createConversation('新会话', store.selectedModelName)
    store.addConversation(conv)
    store.setCurrentConversation(conv.id)
    store.clearMessages()
  }, [])

  /** 切换会话 */
  const switchConversation = useCallback((id: string) => {
    useChatStore.getState().setCurrentConversation(id)
  }, [])

  /** 删除会话 */
  const deleteConversation = useCallback((id: string) => {
    useChatStore.getState().removeConversation(id)
  }, [])

  /** 响应审批（approved/rejected）— 调用后端 resume 端点 */
  const respondApproval = useCallback((approved: boolean) => {
    if (!approvalRequest || !currentConversationId) return

    setApprovalRequest(null)
    setIsLoading(true)

    // 创建 AI 占位消息用于流式接收
    const aiMessageId = generateId()
    const aiMessage: ChatMessage = {
      id: aiMessageId,
      conversationId: currentConversationId,
      role: 'assistant',
      content: '',
      createdAt: Date.now(),
    }
    addMessage(aiMessage)

    abortRef.current = chatResumeStream(
      currentConversationId,
      {
        approved,
        toolName: approvalRequest.tool,
        toolArgs: approvalRequest.args,
        userResponse: approved ? '' : '用户拒绝执行此操作',
      },
      (token: StreamToken) => {
        if (token.done) {
          setIsLoading(false)
          abortRef.current = null
          return
        }
        const currentMessages = useChatStore.getState().messages
        const updatedMessages = currentMessages.map((msg) =>
          msg.id === aiMessageId ? { ...msg, content: msg.content + token.content } : msg
        )
        setMessages(updatedMessages)
      },
      (error) => {
        console.error('[Chat] Resume stream error:', error)
        const currentMessages = useChatStore.getState().messages
        const updatedMessages = currentMessages.map((msg) =>
          msg.id === aiMessageId
            ? { ...msg, content: msg.content || '\n\n⚠️ 审批恢复失败，请重试' }
            : msg
        )
        setMessages(updatedMessages)
        setIsLoading(false)
        abortRef.current = null
      },
      {
        onToolStart: (tool, args) => {
          setToolProgress((prev) => [...prev, { tool, status: 'running', args, startTime: Date.now() }])
        },
        onToolEnd: (tool, outputPreview) => {
          setToolProgress((prev) =>
            prev.map((t) => t.tool === tool && t.status === 'running' ? { ...t, status: 'done', outputPreview } : t)
          )
        },
      }
    )
  }, [approvalRequest, currentConversationId, addMessage, setMessages, setIsLoading])

  return {
    messages,
    conversationId: currentConversationId,
    reasoningDepth,
    isLoading,
    conversations,
    currentConversationId,
    selectedProviderId,
    selectedModelName,
    toolProgress,
    approvalRequest,
    contextSources,
    tokenStats,
    sendMessage,
    sendMessageSync,
    setReasoningDepth,
    setModelSelection,
    submitFeedback: handleFeedback,
    clearMessages,
    stopGeneration,
    createConversation: handleCreateConversation,
    switchConversation,
    deleteConversation,
    respondApproval,
  }
}
