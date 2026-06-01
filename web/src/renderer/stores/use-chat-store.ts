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

  // 模型选择
  selectedProviderId: number | undefined
  selectedModelName: string | undefined

  // 加载状态
  isLoading: boolean

  // 操作
  setConversations: (conversations: Conversation[]) => void
  setCurrentConversation: (id: string | null) => void
  setMessages: (messages: ChatMessage[]) => void
  addMessage: (message: ChatMessage) => void
  setReasoningDepth: (depth: 'fast' | 'deep' | 'full') => void
  setModelSelection: (providerId: number, modelName: string) => void
  setIsLoading: (loading: boolean) => void
  clearMessages: () => void

  // 会话管理
  addConversation: (conv: Conversation) => void
  removeConversation: (id: string) => void
  updateConversation: (id: string, updates: Partial<Conversation>) => void
}

/**
 * 聊天状态 Store
 */
export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  currentConversationId: null,
  messages: [],
  reasoningDepth: 'fast',
  selectedProviderId: undefined,
  selectedModelName: undefined,
  isLoading: false,

  setConversations: (conversations) => set({ conversations }),
  setCurrentConversation: (id) => set({ currentConversationId: id }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  setReasoningDepth: (reasoningDepth) => set({ reasoningDepth }),
  setModelSelection: (providerId, modelName) => set({ selectedProviderId: providerId, selectedModelName: modelName }),
  setIsLoading: (isLoading) => set({ isLoading }),
  clearMessages: () => set({ messages: [] }),

  addConversation: (conv) =>
    set((state) => ({
      conversations: [conv, ...state.conversations],
    })),
  removeConversation: (id) =>
    set((state) => {
      const filtered = state.conversations.filter((c) => c.id !== id)
      const newCurrentId =
        state.currentConversationId === id ? (filtered[0]?.id ?? null) : state.currentConversationId
      return {
        conversations: filtered,
        currentConversationId: newCurrentId,
      }
    }),
  updateConversation: (id, updates) =>
    set((state) => ({
      conversations: state.conversations.map((c) => (c.id === id ? { ...c, ...updates } : c)),
    })),
}))
