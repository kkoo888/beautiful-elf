/**
 * 设置面板测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// Mock useSettings hook
const mockUpdateSettings = vi.fn()
const mockUpdateSoul = vi.fn()
const mockTestConnection = vi.fn()
const mockLoadModels = vi.fn()
const mockClearRestartHint = vi.fn()

const defaultSettings = {
  ollama: {
    baseUrl: 'http://localhost:11434',
    chatModel: 'qwen2.5:7b',
    embedModel: 'nomic-embed-text',
    visionModel: 'llava:7b',
  },
  ai: { temperature: 0.7, maxTokens: 2048, topP: 0.9, systemPrompt: 'test' },
  app: {
    language: 'zh-CN',
    autoLaunch: false,
    minimizeToTray: true,
    closeBehavior: 'minimize' as const,
  },
  privacy: { encryptData: false, logLevel: 'info' as const, anonymousStats: true },
}

const defaultSoul = {
  name: '小助手',
  avatar: '',
  personality: ['温柔'],
  speakingStyle: '温柔亲切',
  emotionalTendency: 60,
  backgroundStory: '',
}

vi.mock('../hooks/use-settings', () => ({
  useSettings: () => ({
    settings: defaultSettings,
    soul: defaultSoul,
    isLoading: false,
    updateSettings: mockUpdateSettings,
    updateSoul: mockUpdateSoul,
    testOllamaConnection: mockTestConnection,
    loadModels: mockLoadModels,
    models: [],
    restartHint: null,
    clearRestartHint: mockClearRestartHint,
  }),
}))

// Mock @/components/page-header
vi.mock('@/components/page-header', () => ({
  PageHeader: ({ title, description }: { title: string; description?: string }) => (
    <div data-testid="page-header">
      <h1>{title}</h1>
      {description && <p>{description}</p>}
    </div>
  ),
}))

import SettingsPanel from '../components/settings-panel'

describe('SettingsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染设置面板标题', () => {
    render(<SettingsPanel />)
    expect(screen.getByText('⚙️ 设置')).toBeTruthy()
  })

  it('渲染所有 Tab 标签', () => {
    render(<SettingsPanel />)
    expect(screen.getByText('Ollama')).toBeTruthy()
    expect(screen.getByText('AI 参数')).toBeTruthy()
    expect(screen.getByText('应用')).toBeTruthy()
    expect(screen.getByText('快捷键')).toBeTruthy()
    expect(screen.getByText('隐私安全')).toBeTruthy()
    expect(screen.getByText('关于')).toBeTruthy()
    expect(screen.getByText('灵魂')).toBeTruthy()
  })

  it('默认显示 Ollama 配置', () => {
    render(<SettingsPanel />)
    expect(screen.getByText('服务地址')).toBeTruthy()
    expect(screen.getByDisplayValue('http://localhost:11434')).toBeTruthy()
  })

  it('切换到 AI 参数 Tab', async () => {
    render(<SettingsPanel />)
    fireEvent.click(screen.getByText('AI 参数'))
    await waitFor(() => {
      expect(screen.getByText('温度 (Temperature)')).toBeTruthy()
    })
  })

  it('切换到灵魂 Tab', async () => {
    render(<SettingsPanel />)
    fireEvent.click(screen.getByText('灵魂'))
    await waitFor(() => {
      expect(screen.getByText('助手名称')).toBeTruthy()
      expect(screen.getByText('性格标签（可多选）')).toBeTruthy()
    })
  })

  it('切换到关于 Tab 显示版本信息', async () => {
    render(<SettingsPanel />)
    fireEvent.click(screen.getByText('关于'))
    await waitFor(() => {
      expect(screen.getByText('Beautiful Elf')).toBeTruthy()
    })
  })

  it('切换到隐私安全 Tab', async () => {
    render(<SettingsPanel />)
    fireEvent.click(screen.getByText('隐私安全'))
    await waitFor(() => {
      expect(screen.getByText('启用数据加密')).toBeTruthy()
      expect(screen.getByText('日志级别')).toBeTruthy()
    })
  })
})
