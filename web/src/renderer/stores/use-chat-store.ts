import { create } from 'zustand'
import type { ChatMessage, Conversation } from '@/types'

interface ChatState {
  // 会话列表
  conversations: Conversation[]
  currentConversationId: string | null

  // 消息列表
  messages: ChatMessage[]

  // 推理深度
  reasoningDepth: 'fast' | 'deep' | 'full'

  // 加载状态
  isLoading: boolean

  // 操作
  setConversations: (conversations: Conversation[]) => void
  setCurrentConversationId: (id: string | null) => void
  setMessages: (messages: ChatMessage[]) => void
  addMessage: (message: ChatMessage) => void
  setReasoningDepth: (depth: 'fast' | 'deep' | 'full') => void
  setIsLoading: (loading: boolean) => void
  clearMessages: () => void
}

/**
 * 聊天状态 Store
 */
export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  currentConversationId: null,
  messages: [],
  reasoningDepth: 'fast',
  isLoading: false,

  setConversations: (conversations) => set({ conversations }),
  setCurrentConversationId: (id) => set({ currentConversationId: id }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message]
    })),
  setReasoningDepth: (reasoningDepth) => set({ reasoningDepth }),
  setIsLoading: (isLoading) => set({ isLoading }),
  clearMessages: () => set({ messages: [] })
}))
