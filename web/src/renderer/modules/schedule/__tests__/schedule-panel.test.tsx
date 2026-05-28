/** SchedulePanel 单元测试 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import React from 'react'
import { SchedulePanel } from '../components/schedule-panel'

// Mock dayjs 固定时间
vi.mock('dayjs', async () => {
  const actual = await vi.importActual<typeof import('dayjs')>('dayjs')
  const fixedDate = actual.default('2026-05-28T10:00:00+08:00')
  const dayjs = (...args: Parameters<typeof actual.default>) => {
    if (args.length === 0) return fixedDate
    return actual.default(...args)
  }
  dayjs.extend = actual.default.extend
  dayjs.locale = actual.default.locale
  dayjs.isDayjs = actual.default.isDayjs
  return { default: dayjs, ...actual }
})

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

describe('SchedulePanel', () => {
  it('渲染日程面板标题', () => {
    renderWithProviders(<SchedulePanel />)
    expect(screen.getByText(/日程/)).toBeDefined()
  })

  it('显示新建按钮', () => {
    renderWithProviders(<SchedulePanel />)
    expect(screen.getByText('新建')).toBeDefined()
  })

  it('显示搜索框', () => {
    renderWithProviders(<SchedulePanel />)
    expect(screen.getByPlaceholderText('搜索日程...')).toBeDefined()
  })

  it('显示视图切换控件', () => {
    renderWithProviders(<SchedulePanel />)
    expect(screen.getByText('月')).toBeDefined()
    expect(screen.getByText('周')).toBeDefined()
    expect(screen.getByText('日')).toBeDefined()
  })

  it('显示今天按钮', () => {
    renderWithProviders(<SchedulePanel />)
    expect(screen.getByText('今天')).toBeDefined()
  })

  it('点击新建按钮打开表单', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SchedulePanel />)
    await user.click(screen.getByText('新建'))
    expect(screen.getByText('新建日程')).toBeDefined()
  })
})
