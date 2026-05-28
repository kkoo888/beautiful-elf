/**
 * ChatPanel 组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ChatPanel } from '../components/chat-panel'

// Mock the useChat hook
const mockSendMessage = vi.fn()
const mockSetReasoningDepth = vi.fn()
const mockSubmitFeedback = vi.fn()
const mockClearMessages = vi.fn()
const mockStopGeneration = vi.fn()

vi.mock('../hooks/use-chat', () => ({
  useChat: () => ({
    messages: [],
    conversationId: null,
    reasoningDepth: 'fast' as const,
    isLoading: false,
    sendMessage: mockSendMessage,
    sendMessageSync: vi.fn(),
    setReasoningDepth: mockSetReasoningDepth,
    submitFeedback: mockSubmitFeedback,
    clearMessages: mockClearMessages,
    stopGeneration: mockStopGeneration
  })
}))

// Mock child components
vi.mock('../components/message-list', () => ({
  SimpleMessageList: ({ messages }: { messages: unknown[] }) => (
    <div data-testid="message-list">{messages.length} messages</div>
  )
}))

vi.mock('../components/message-input', () => ({
  MessageInput: ({ onSend }: { onSend: (v: string) => void }) => (
    <div data-testid="message-input">
      <button onClick={() => onSend('test message')}>Send</button>
    </div>
  )
}))

vi.mock('../components/reasoning-depth', () => ({
  ReasoningDepthSwitch: () => <div data-testid="reasoning-switch" />
}))

describe('ChatPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the chat panel with title', () => {
    render(<ChatPanel />)
    expect(screen.getByText('💬 对话')).toBeDefined()
  })

  it('renders message list', () => {
    render(<ChatPanel />)
    expect(screen.getByTestId('message-list')).toBeDefined()
  })

  it('renders message input', () => {
    render(<ChatPanel />)
    expect(screen.getByTestId('message-input')).toBeDefined()
  })

  it('renders reasoning depth switch', () => {
    render(<ChatPanel />)
    expect(screen.getByTestId('reasoning-switch')).toBeDefined()
  })

  it('sends message when input triggers send', () => {
    render(<ChatPanel />)
    const sendButton = screen.getByText('Send')
    fireEvent.click(sendButton)
    expect(mockSendMessage).toHaveBeenCalledWith('test message')
  })

  it('renders clear button', () => {
    render(<ChatPanel />)
    expect(screen.getByRole('button', { name: /清空对话/i })).toBeDefined()
  })
})
