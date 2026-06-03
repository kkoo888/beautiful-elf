/** SkillsPanel 单元测试 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import React from 'react'
import SkillsPanel from '../components/skills-panel'

// Mock API 模块
vi.mock('../services/skills-api', () => ({
  fetchSkills: vi.fn().mockResolvedValue([
    {
      id: 'skill_001',
      name: 'weather',
      description: '获取当前天气和预报',
      version: '1.2.0',
      enabled: true,
      triggerWords: ['天气', '气温'],
      dependencies: [],
      stats: { callCount: 128, successRate: 0.97, avgDuration: 850 },
      createdAt: '2026-01-01T00:00:00Z',
    },
    {
      id: 'skill_002',
      name: 'github',
      description: '与 GitHub 交互',
      version: '2.0.1',
      enabled: false,
      triggerWords: ['github', 'issue'],
      dependencies: ['gh'],
      stats: { callCount: 64, successRate: 0.92, avgDuration: 1200 },
      createdAt: '2026-01-01T00:00:00Z',
    },
  ]),
  installSkill: vi.fn().mockResolvedValue({
    id: 'skill_new',
    name: 'new-skill',
    description: '新安装的技能',
    version: '0.1.0',
    enabled: true,
    triggerWords: [],
    dependencies: [],
    stats: { callCount: 0, successRate: 1, avgDuration: 0 },
    createdAt: '2026-05-28T00:00:00Z',
  }),
  toggleSkill: vi.fn().mockResolvedValue({
    id: 'skill_001',
    name: 'weather',
    description: '获取当前天气和预报',
    version: '1.2.0',
    enabled: false,
    triggerWords: ['天气', '气温'],
    dependencies: [],
    stats: { callCount: 128, successRate: 0.97, avgDuration: 850 },
    createdAt: '2026-01-01T00:00:00Z',
  }),
  fetchSkillStats: vi
    .fn()
    .mockResolvedValue({ callCount: 128, successRate: 0.97, avgDuration: 850 }),
  refineSkill: vi.fn().mockResolvedValue({
    suggestions: ['建议一', '建议二'],
    refinedContent: '# weather (Refined)\n\n优化后的内容',
  }),
}))

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider>{ui}</ConfigProvider>
    </QueryClientProvider>
  )
}

describe('SkillsPanel', () => {
  it('渲染技能面板标题', async () => {
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText(/技能/)).toBeDefined()
    })
  })

  it('显示安装技能按钮', async () => {
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText('安装技能')).toBeDefined()
    })
  })

  it('显示链式配置按钮', async () => {
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText('链式配置')).toBeDefined()
    })
  })

  it('显示搜索框', async () => {
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/搜索技能/)).toBeDefined()
    })
  })

  it('渲染技能卡片', async () => {
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText('weather')).toBeDefined()
      expect(screen.getByText('github')).toBeDefined()
    })
  })

  it('显示技能描述', async () => {
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText('获取当前天气和预报')).toBeDefined()
    })
  })

  it('显示技能版本', async () => {
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText('v1.2.0')).toBeDefined()
      expect(screen.getByText('v2.0.1')).toBeDefined()
    })
  })

  it('显示统计信息', async () => {
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText('128')).toBeDefined()
    })
  })

  it('点击安装技能按钮打开安装面板', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText('安装技能')).toBeDefined()
    })
    await user.click(screen.getByText('安装技能'))
    await waitFor(() => {
      expect(screen.getByText(/从文件夹安装/)).toBeDefined()
    })
  })

  it('点击技能卡片打开详情', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText('weather')).toBeDefined()
    })
    await user.click(screen.getByText('weather'))
    await waitFor(() => {
      expect(screen.getByText('SKILL.md')).toBeDefined()
    })
  })

  it('搜索过滤技能', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SkillsPanel />)
    await waitFor(() => {
      expect(screen.getByText('weather')).toBeDefined()
    })
    const searchInput = screen.getByPlaceholderText(/搜索技能/)
    await user.type(searchInput, 'github')
    await waitFor(() => {
      expect(screen.queryByText('weather')).toBeNull()
      expect(screen.getByText('github')).toBeDefined()
    })
  })
})
