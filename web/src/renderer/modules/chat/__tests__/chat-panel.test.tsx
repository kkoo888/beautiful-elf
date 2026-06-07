/**
 * ChatContent 组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ChatContent } from '../components/chat-panel'

// Mock 子组件
vi.mock('../components/message-list', () => ({
  SimpleMessageList: ({ messages }: { messages: unknown[] }) => (
    <div data-testid="message-list">{messages.length} messages</div>
  ),
}))

vi.mock('../components/message-input', () => ({
  MessageInput: ({ onSend }: { onSend: (v: string) => void }) => (
    <div data-testid="message-input">
      <button onClick={() => onSend('test message')}>Send</button>
    </div>
  ),
}))

vi.mock('../components/reasoning-depth', () => ({
  ReasoningDepthSwitch: () => <div data-testid="reasoning-switch" />,
}))

vi.mock('@/modules/shared/components/model-selector', () => ({
  FullModelSelect: () => <div data-testid="model-select" />,
}))

function createMockChat(overrides = {}) {
  return {
    messages: [],
    conversationId: null,
    reasoningDepth: 'fast' as const,
    isLoading: false,
    conversations: [],
    currentConversationId: null,
    selectedProviderId: undefined,
    selectedModelName: undefined,
    toolProgress: [],
    approvalRequest: null,
    contextSources: [],
    tokenStats: null,
    sendMessage: vi.fn(),
    sendMessageSync: vi.fn(),
    setReasoningDepth: vi.fn(),
    setModelSelection: vi.fn(),
    submitFeedback: vi.fn(),
    clearMessages: vi.fn(),
    stopGeneration: vi.fn(),
    createConversation: vi.fn(),
    switchConversation: vi.fn(),
    deleteConversation: vi.fn(),
    respondApproval: vi.fn(),
    ...overrides,
  }
}

describe('ChatContent', () => {
  it('renders the chat panel with title', () => {
    render(<ChatContent chat={createMockChat()} />)
    expect(screen.getByText('💬 对话')).toBeDefined()
  })

  it('renders message list', () => {
    render(<ChatContent chat={createMockChat()} />)
    expect(screen.getByTestId('message-list')).toBeDefined()
  })

  it('renders message input', () => {
    render(<ChatContent chat={createMockChat()} />)
    expect(screen.getByTestId('message-input')).toBeDefined()
  })

  it('renders reasoning depth switch', () => {
    render(<ChatContent chat={createMockChat()} />)
    expect(screen.getByTestId('reasoning-switch')).toBeDefined()
  })

  it('sends message when input triggers send', () => {
    const mockSendMessage = vi.fn()
    render(<ChatContent chat={createMockChat({ sendMessage: mockSendMessage })} />)
    const sendButton = screen.getByText('Send')
    fireEvent.click(sendButton)
    expect(mockSendMessage).toHaveBeenCalledWith('test message')
  })
})
