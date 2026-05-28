import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ClipboardPanel } from './clipboard-panel'

// Mock API
vi.mock('../services/clipboard-api', () => ({
  fetchClipboardList: vi.fn().mockResolvedValue({
    items: [
      {
        id: '1',
        content: 'npm install react-window',
        contentType: 'code',
        language: 'bash',
        isPinned: true,
        copiedAt: '2026-05-28T10:30:00Z',
        createdAt: '2026-05-28T10:30:00Z',
      },
      {
        id: '2',
        content: '普通文本内容',
        contentType: 'text',
        isPinned: false,
        copiedAt: '2026-05-28T10:25:00Z',
        createdAt: '2026-05-28T10:25:00Z',
      },
    ],
    total: 2,
    page: 1,
    pageSize: 50,
  }),
  deleteClipboardItem: vi.fn().mockResolvedValue(undefined),
  togglePinClipboardItem: vi.fn().mockResolvedValue({
    id: '2',
    content: '普通文本内容',
    contentType: 'text',
    isPinned: true,
    copiedAt: '2026-05-28T10:25:00Z',
    createdAt: '2026-05-28T10:25:00Z',
  }),
}))

// Mock useDebounce to return value immediately
vi.mock('@/hooks', () => ({
  useDebounce: <T,>(value: T) => value,
}))

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
})

describe('ClipboardPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render the panel title', async () => {
    render(<ClipboardPanel />)
    expect(screen.getByText('剪贴板')).toBeInTheDocument()
  })

  it('should render search input', async () => {
    render(<ClipboardPanel />)
    expect(screen.getByPlaceholderText('搜索剪贴板内容...')).toBeInTheDocument()
  })

  it('should load and display clipboard items', async () => {
    render(<ClipboardPanel />)

    await waitFor(() => {
      expect(screen.getByText('npm install react-window')).toBeInTheDocument()
      expect(screen.getByText('普通文本内容')).toBeInTheDocument()
    })
  })

  it('should show pinned items with pin badge', async () => {
    render(<ClipboardPanel />)

    await waitFor(() => {
      expect(screen.getByText('📌')).toBeInTheDocument()
    })
  })

  it('should update search keyword on input', async () => {
    render(<ClipboardPanel />)

    const input = screen.getByPlaceholderText('搜索剪贴板内容...')
    fireEvent.change(input, { target: { value: 'react' } })

    expect(input).toHaveValue('react')
  })
})
