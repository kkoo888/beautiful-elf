import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import { SnippetsPanel } from '../components/snippets-panel'

// Mock API
vi.mock('../services/snippets-api', () => ({
  fetchSnippets: vi.fn().mockResolvedValue({
    items: [
      {
        id: '1',
        title: 'Test Snippet',
        content: 'console.log("hello")',
        language: 'javascript',
        tags: ['test'],
        useCount: 5,
        createdAt: '2026-05-01T10:00:00Z',
        updatedAt: '2026-05-20T14:30:00Z'
      }
    ],
    total: 1,
    page: 1,
    pageSize: 20
  }),
  fetchAllTags: vi.fn().mockResolvedValue(['test', 'react']),
  createSnippet: vi.fn().mockResolvedValue({
    id: '2',
    title: 'New Snippet',
    content: 'code',
    language: 'python',
    tags: [],
    useCount: 0,
    createdAt: '2026-05-28T10:00:00Z',
    updatedAt: '2026-05-28T10:00:00Z'
  }),
  updateSnippet: vi.fn().mockResolvedValue({}),
  deleteSnippet: vi.fn().mockResolvedValue(undefined),
  recordSnippetUse: vi.fn().mockResolvedValue(undefined)
}))

// Mock theme hook
vi.mock('@/hooks/use-theme', () => ({
  useTheme: () => ({ theme: 'light', isDark: false, toggleTheme: vi.fn() })
}))

// Mock clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined)
  }
})

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider>{ui}</ConfigProvider>
    </QueryClientProvider>
  )
}

describe('SnippetsPanel', () => {
  it('should render panel title', async () => {
    renderWithProviders(<SnippetsPanel />)
    expect(screen.getByText('💻 代码片段')).toBeTruthy()
  })

  it('should show new snippet button', () => {
    renderWithProviders(<SnippetsPanel />)
    expect(screen.getByText('新建片段')).toBeTruthy()
  })

  it('should show search input', () => {
    renderWithProviders(<SnippetsPanel />)
    expect(screen.getByPlaceholderText('搜索标题、内容、标签...')).toBeTruthy()
  })

  it('should display snippet cards after loading', async () => {
    renderWithProviders(<SnippetsPanel />)
    await waitFor(() => {
      expect(screen.getByText('Test Snippet')).toBeTruthy()
    })
  })

  it('should show language tag on card', async () => {
    renderWithProviders(<SnippetsPanel />)
    await waitFor(() => {
      expect(screen.getByText('javascript')).toBeTruthy()
    })
  })
})
