/**
 * MessageBubble 组件测试
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageBubble } from '../components/message-bubble'
import type { ChatMessage } from '../types/chat'

// Mock react-markdown
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="markdown">{children}</div>,
}))

// Mock remark-gfm
vi.mock('remark-gfm', () => ({
  default: () => null,
}))

// Mock prismjs
vi.mock('prismjs', () => ({
  default: {
    languages: { plaintext: {} },
    highlight: (code: string) => code,
    highlightAll: vi.fn(),
  },
}))

vi.mock('prismjs/components/prism-typescript', () => ({}))
vi.mock('prismjs/components/prism-javascript', () => ({}))
vi.mock('prismjs/components/prism-python', () => ({}))
vi.mock('prismjs/components/prism-json', () => ({}))
vi.mock('prismjs/components/prism-bash', () => ({}))
vi.mock('prismjs/components/prism-css', () => ({}))
vi.mock('prismjs/components/prism-markdown', () => ({}))
vi.mock('prismjs/components/prism-yaml', () => ({}))
vi.mock('prismjs/components/prism-sql', () => ({}))
vi.mock('prismjs/components/prism-rust', () => ({}))
vi.mock('prismjs/components/prism-go', () => ({}))

describe('MessageBubble', () => {
  const baseMessage: ChatMessage = {
    id: 'test-1',
    conversationId: 'conv-1',
    role: 'user',
    content: '你好',
    createdAt: Date.now(),
  }

  it('renders user message correctly', () => {
    render(<MessageBubble message={baseMessage} />)
    expect(screen.getByText('你好')).toBeDefined()
  })

  it('renders assistant message with markdown', () => {
    const aiMessage: ChatMessage = {
      ...baseMessage,
      id: 'test-2',
      role: 'assistant',
      content: '**加粗文本**',
    }
    render(<MessageBubble message={aiMessage} />)
    expect(screen.getByTestId('markdown')).toBeDefined()
  })

  it('shows quick answer badge when cached', () => {
    const cachedMessage: ChatMessage = {
      ...baseMessage,
      id: 'test-3',
      role: 'assistant',
      content: '快速回答',
      metadata: { isCached: true },
    }
    render(<MessageBubble message={cachedMessage} />)
    expect(screen.getByText('快速回答')).toBeDefined()
  })

  it('shows intent route badge', () => {
    const routedMessage: ChatMessage = {
      ...baseMessage,
      id: 'test-4',
      role: 'assistant',
      content: '路由回答',
      metadata: {
        intentRoute: { module: 'schedule', confidence: 0.95 },
      },
    }
    render(<MessageBubble message={routedMessage} />)
    expect(screen.getByText(/schedule/)).toBeDefined()
  })

  it('shows feedback buttons for assistant messages', () => {
    const aiMessage: ChatMessage = {
      ...baseMessage,
      id: 'test-5',
      role: 'assistant',
      content: '反馈测试',
    }
    const onFeedback = vi.fn()
    render(<MessageBubble message={aiMessage} onFeedback={onFeedback} />)
    expect(screen.getByLabelText('有帮助')).toBeDefined()
    expect(screen.getByLabelText('没帮助')).toBeDefined()
  })

  it('does not show feedback buttons for user messages', () => {
    const onFeedback = vi.fn()
    render(<MessageBubble message={baseMessage} onFeedback={onFeedback} />)
    expect(screen.queryByLabelText('有帮助')).toBeNull()
  })
})
