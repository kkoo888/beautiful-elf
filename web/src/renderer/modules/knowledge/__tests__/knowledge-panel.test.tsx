import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { KnowledgePanel } from '../components/knowledge-panel'

// Mock antd message
vi.mock('antd', async () => {
  const antd = await vi.importActual<typeof import('antd')>('antd')
  return {
    ...antd,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  }
})

describe('KnowledgePanel', () => {
  it('renders the page header', async () => {
    render(<KnowledgePanel />)

    expect(screen.getByText('📚 知识库')).toBeInTheDocument()
    expect(screen.getByText('导入文档，让 AI 学习你的知识')).toBeInTheDocument()
  })

  it('renders upload zone', async () => {
    render(<KnowledgePanel />)

    expect(screen.getByText(/点击或拖拽文件到此区域上传/)).toBeInTheDocument()
  })

  it('renders search input', async () => {
    render(<KnowledgePanel />)

    expect(screen.getByPlaceholderText('搜索文档名称...')).toBeInTheDocument()
  })

  it('renders export button', async () => {
    render(<KnowledgePanel />)

    expect(screen.getByText('导出')).toBeInTheDocument()
  })

  it('renders document list after loading', async () => {
    render(<KnowledgePanel />)

    await waitFor(() => {
      expect(screen.getByText('产品需求文档.pdf')).toBeInTheDocument()
    })

    expect(screen.getByText('API接口文档.md')).toBeInTheDocument()
    expect(screen.getByText('用户手册.docx')).toBeInTheDocument()
  })

  it('switches to recycle bin view', async () => {
    const user = userEvent.setup()
    render(<KnowledgePanel />)

    await waitFor(() => {
      expect(screen.getByText('产品需求文档.pdf')).toBeInTheDocument()
    })

    const recycleTab = screen.getByText('回收站')
    await user.click(recycleTab)

    await waitFor(() => {
      expect(screen.getByText('旧版配置.json')).toBeInTheDocument()
    })
  })
})
