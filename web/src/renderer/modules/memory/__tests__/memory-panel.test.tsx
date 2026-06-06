/** 记忆面板测试 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import type { ReactNode } from 'react'
import MemoryPanel from '../components/memory-panel'

// Mock API
vi.mock('../services/memory-api', () => ({
  fetchMemories: vi.fn().mockResolvedValue({
    items: [
      {
        id: 'test-1',
        summary: '测试记忆摘要',
        content: '测试记忆完整内容',
        conversationId: 'conv-001',
        tags: ['测试'],
        createdAt: new Date().toISOString(),
      },
    ],
    total: 1,
    page: 1,
    pageSize: 20,
  }),
  searchMemories: vi.fn().mockResolvedValue({
    items: [
      {
        id: 'test-1',
        summary: '测试记忆摘要',
        content: '测试记忆完整内容',
        conversationId: 'conv-001',
        tags: ['测试'],
        similarity: 0.92,
        createdAt: new Date().toISOString(),
      },
    ],
    query: '测试',
  }),
  deleteMemory: vi.fn().mockResolvedValue(undefined),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <ConfigProvider>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </ConfigProvider>
    )
  }
}

describe('MemoryPanel', () => {
  it('should render page header', async () => {
    const Wrapper = createWrapper()
    render(<MemoryPanel />, { wrapper: Wrapper })

    expect(screen.getByText('🧠 记忆')).toBeInTheDocument()
    expect(screen.getByText('长期记忆与语义检索')).toBeInTheDocument()
  })

  it('should render search input', () => {
    const Wrapper = createWrapper()
    render(<MemoryPanel />, { wrapper: Wrapper })

    expect(screen.getByPlaceholderText('输入问题，语义检索相关记忆…')).toBeInTheDocument()
  })

  it('should render memory cards after loading', async () => {
    const Wrapper = createWrapper()
    render(<MemoryPanel />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('测试记忆摘要')).toBeInTheDocument()
    })
  })

  it('should show empty state when no memories', async () => {
    const { fetchMemories } = await import('../services/memory-api')
    vi.mocked(fetchMemories).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      pageSize: 20,
    })

    const Wrapper = createWrapper()
    render(<MemoryPanel />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('AI 会从对话中提炼记忆，自动记录在这里')).toBeInTheDocument()
    })
  })

  it('should trigger search on Enter', async () => {
    const Wrapper = createWrapper()
    render(<MemoryPanel />, { wrapper: Wrapper })

    const input = screen.getByPlaceholderText('输入问题，语义检索相关记忆…')
    fireEvent.change(input, { target: { value: '测试' } })
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })

    await waitFor(() => {
      expect(screen.getByText(/找到/)).toBeInTheDocument()
    })
  })
})
