/** 设置系统 API 服务（Mock 实现） */

import type {
  AppSettings,
  SoulConfig,
  OllamaModel,
  ConnectionTestResult
} from '../types/settings'

/** 模拟延迟 */
const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms))

/** 默认设置 */
const DEFAULT_SETTINGS: AppSettings = {
  ollama: {
    baseUrl: 'http://localhost:11434',
    chatModel: 'qwen2.5:7b',
    embedModel: 'nomic-embed-text',
    visionModel: 'llava:7b'
  },
  ai: {
    temperature: 0.7,
    maxTokens: 2048,
    topP: 0.9,
    systemPrompt: '你是一个友好的 AI 助手。'
  },
  app: {
    language: 'zh-CN',
    autoLaunch: false,
    minimizeToTray: true,
    closeBehavior: 'minimize'
  },
  privacy: {
    encryptData: false,
    logLevel: 'info',
    anonymousStats: true
  }
}

/** 默认灵魂配置 */
const DEFAULT_SOUL: SoulConfig = {
  name: '小助手',
  avatar: '',
  personality: ['温柔', '聪明'],
  speakingStyle: '温柔亲切',
  emotionalTendency: 60,
  backgroundStory: ''
}

/** Mock 模型列表 */
const MOCK_MODELS: OllamaModel[] = [
  { name: 'qwen2.5:7b', size: 4_400_000_000, modifiedAt: '2025-05-20T10:00:00Z' },
  { name: 'qwen2.5:14b', size: 8_900_000_000, modifiedAt: '2025-05-18T10:00:00Z' },
  { name: 'llama3.1:8b', size: 4_700_000_000, modifiedAt: '2025-05-15T10:00:00Z' },
  { name: 'nomic-embed-text', size: 274_000_000, modifiedAt: '2025-05-10T10:00:00Z' },
  { name: 'llava:7b', size: 4_000_000_000, modifiedAt: '2025-05-12T10:00:00Z' }
]

/** localStorage 键名 */
const SETTINGS_KEY = 'beautiful-elf:settings'
const SOUL_KEY = 'beautiful-elf:soul'

/**
 * 获取应用设置
 */
export async function getSettings(): Promise<AppSettings> {
  await delay(200)
  try {
    const stored = localStorage.getItem(SETTINGS_KEY)
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }
    }
  } catch {
    // fallback to default
  }
  return { ...DEFAULT_SETTINGS }
}

/**
 * 保存应用设置（部分更新）
 */
export async function saveSettings(
  partial: Partial<AppSettings>
): Promise<AppSettings> {
  await delay(100)
  const current = await getSettings()
  const merged: AppSettings = {
    ollama: { ...current.ollama, ...partial.ollama },
    ai: { ...current.ai, ...partial.ai },
    app: { ...current.app, ...partial.app },
    privacy: { ...current.privacy, ...partial.privacy }
  }
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(merged))
  return merged
}

/**
 * 获取灵魂配置
 */
export async function getSoulConfig(): Promise<SoulConfig> {
  await delay(200)
  try {
    const stored = localStorage.getItem(SOUL_KEY)
    if (stored) {
      return { ...DEFAULT_SOUL, ...JSON.parse(stored) }
    }
  } catch {
    // fallback to default
  }
  return { ...DEFAULT_SOUL }
}

/**
 * 保存灵魂配置
 */
export async function saveSoulConfig(config: SoulConfig): Promise<SoulConfig> {
  await delay(100)
  localStorage.setItem(SOUL_KEY, JSON.stringify(config))
  return config
}

/**
 * 测试 Ollama 连接
 */
export async function testConnection(
  baseUrl: string
): Promise<ConnectionTestResult> {
  await delay(800 + Math.random() * 500)
  // Mock：localhost 始终成功，其他随机
  if (baseUrl.includes('localhost') || baseUrl.includes('127.0.0.1')) {
    return { success: true, message: '连接成功！', latency: 12 }
  }
  const ok = Math.random() > 0.3
  return ok
    ? { success: true, message: '连接成功！', latency: 45 }
    : { success: false, message: '无法连接到 Ollama 服务，请检查地址是否正确。' }
}

/**
 * 获取可用模型列表
 */
export async function fetchModels(_baseUrl?: string): Promise<OllamaModel[]> {
  await delay(500)
  return [...MOCK_MODELS]
}
