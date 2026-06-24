import { create } from 'zustand'
import type { ChatMessage, Conversation } from '@/types'

interface ChatState {
  // 会话列表
  conversations: Conversation[]
  currentConversationId: string | null

  // 消息列表
  messages: ChatMessage[]

  // 推理深度
  reasoningDepth: 'auto' | 'fast' | 'deep' | 'full'

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
  setReasoningDepth: (depth: 'auto' | 'fast' | 'deep' | 'full') => void
  setModelSelection: (providerId: number, modelName: string) => void
  /** 从已启用供应商列表中提取默认供应商和模型，写入 store */
  initDefaultModel: (providers: { id: number; isDefault: number; models: { modelName: string }[] }[]) => void
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
  reasoningDepth: 'auto',
  selectedProviderId: undefined,
  selectedModelName: 'auto',
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
  initDefaultModel: (providers) => {
    const defaultP = providers.find((p) => p.isDefault === 1) ?? providers[0]
    if (defaultP && defaultP.models.length > 0) {
      set({ selectedProviderId: defaultP.id, selectedModelName: 'auto' })
    }
  },
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
