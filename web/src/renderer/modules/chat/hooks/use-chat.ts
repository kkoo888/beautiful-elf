/**
 * 聊天状态管理 Hook
 * 基于 useChatStore，提供聊天操作方法
 */

import { useCallback, useRef } from 'react'
import { useChatStore } from '@/stores/use-chat-store'
import { chat, chatStream, submitFeedback, createConversation } from '../services/chat-api'
import type {
  ChatMessage,
  Conversation,
  FeedbackData,
  ReasoningDepth,
  StreamToken,
} from '../types/chat'

/** 生成唯一 ID */
const generateId = (): string => crypto.randomUUID()

interface UseChatReturn {
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

  /** 确保有会话 ID（调用后端创建） */
  const ensureConversationId = useCallback(async (): Promise<string> => {
    if (currentConversationId) return currentConversationId
    const conv = await createConversation('新会话')
    console.log('[Chat] createConversation result:', conv)
    if (!conv) throw new Error('createConversation returned undefined')
    useChatStore.getState().addConversation(conv)
    useChatStore.getState().setCurrentConversation(conv.id)
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
      abortRef.current = chatStream(
        {
          conversationId: convId,
          message: content.trim(),
          reasoningDepth,
          providerId: selectedProviderId,
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
        }
      )
    },
    [isLoading, reasoningDepth, ensureConversationId, addMessage, setMessages, setIsLoading]
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
        const response = await chat({
          conversationId: convId,
          message: content.trim(),
          reasoningDepth,
          providerId: selectedProviderId,
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
    [isLoading, reasoningDepth, ensureConversationId, addMessage, setIsLoading]
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
        await submitFeedback({
          messageId: data.messageId,
          type: data.type,
          reasons: data.reasons,
          comment: data.comment,
        })

        // 更新本地消息的反馈状态
        const currentMessages = useChatStore.getState().messages
        const updatedMessages = currentMessages.map((msg) =>
          msg.id === data.messageId ? { ...msg, feedback: data } : msg
        )
        setMessages(updatedMessages)
      } catch (error) {
        console.error('[Chat] Feedback error:', error)
      }
    },
    [setMessages]
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
    const conv = await createConversation('新会话')
    useChatStore.getState().addConversation(conv)
    useChatStore.getState().setCurrentConversation(conv.id)
    useChatStore.getState().clearMessages()
  }, [])

  /** 切换会话 */
  const switchConversation = useCallback((id: string) => {
    useChatStore.getState().setCurrentConversation(id)
  }, [])

  /** 删除会话 */
  const deleteConversation = useCallback((id: string) => {
    useChatStore.getState().removeConversation(id)
  }, [])

  return {
    messages,
    conversationId: currentConversationId,
    reasoningDepth,
    isLoading,
    conversations,
    currentConversationId,
    selectedProviderId,
    selectedModelName,
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
  }
}
