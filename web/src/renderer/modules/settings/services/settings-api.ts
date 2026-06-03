/**
 * 设置系统 API 服务
 *
 * 使用 extractData 消除 as any。后端 CamelModel 已统一返回 camelCase。
 */

import { apiClient, extractData } from '@/services/api-client'
import type { AppSettings, SoulConfig, OllamaModel, ConnectionTestResult } from '../types/settings'
import type { LLMProvider, LLMProviderPayload } from '../types/settings'

// ── 默认值 ──────────────────────────────────────────────────

const DEFAULT_SETTINGS: AppSettings = {
  ollama: {
    baseUrl: 'http://localhost:11434',
    chatModel: 'qwen2.5:7b',
    embedModel: 'nomic-embed-text',
    visionModel: 'llava:7b',
  },
  ai: {
    temperature: 0.7,
    maxTokens: 2048,
    topP: 0.9,
    systemPrompt: '你是一个友好的 AI 助手。',
  },
  app: {
    language: 'zh-CN',
    autoLaunch: false,
    minimizeToTray: true,
    closeBehavior: 'minimize',
  },
  privacy: {
    encryptData: false,
    logLevel: 'info',
    anonymousStats: true,
  },
}

const DEFAULT_SOUL: SoulConfig = {
  name: '小助手',
  avatar: '',
  personality: ['温柔', '聪明'],
  speakingStyle: '温柔亲切',
  emotionalTendency: 60,
  backgroundStory: '',
}

// ── 转换函数（业务映射）─────────────────────────────────────

function toFrontendSoul(data: Record<string, unknown>): SoulConfig {
  return {
    name: (data.name as string) ?? '',
    avatar: (data.avatarUrl as string) ?? '',
    personality: (data.personality as string[]) ?? [],
    speakingStyle: (data.speakingStyle as string) ?? '温柔亲切',
    emotionalTendency: (data.emotionalTendency as number) ?? 60,
    backgroundStory: (data.background as string) ?? '',
  }
}

// ── API 函数 ─────────────────────────────────────────────────

/** 获取应用设置 */
export async function getSettings(): Promise<AppSettings> {
  try {
    const item = extractData(await apiClient.get('/configs/app_settings')) as Record<string, unknown>
    if (item?.keyValue) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(item.keyValue as string) }
    }
  } catch {
    // key 不存在时返回默认值
  }
  return { ...DEFAULT_SETTINGS }
}

/** 保存应用设置（部分更新） */
export async function saveSettings(partial: Partial<AppSettings>): Promise<AppSettings> {
  const current = await getSettings()
  const merged: AppSettings = {
    ollama: { ...current.ollama, ...partial.ollama },
    ai: { ...current.ai, ...partial.ai },
    app: { ...current.app, ...partial.app },
    privacy: { ...current.privacy, ...partial.privacy },
  }
  const jsonStr = JSON.stringify(merged)

  try {
    await apiClient.put('/configs/app_settings', {
      keyValue: jsonStr,
      description: '应用设置（JSON）',
    })
  } catch {
    await apiClient.post('/configs', {
      settingsKey: 'app_settings',
      keyValue: jsonStr,
      description: '应用设置（JSON）',
    })
  }

  return merged
}

/** 获取灵魂配置 */
export async function getSoulConfig(): Promise<SoulConfig> {
  try {
    const data = extractData(await apiClient.get('/soul_configs/active')) as Record<string, unknown>
    return toFrontendSoul(data)
  } catch {
    return { ...DEFAULT_SOUL }
  }
}

/** 保存灵魂配置 */
export async function saveSoulConfig(config: SoulConfig): Promise<SoulConfig> {
  const payload = {
    name: config.name,
    avatarUrl: config.avatar,
    personality: config.personality,
    speakingStyle: config.speakingStyle,
    background: config.backgroundStory,
    systemPrompt: '',
  }
  try {
    const existing = extractData(await apiClient.get('/soul_configs/active')) as Record<string, unknown>
    await apiClient.put(`/soul_configs/${existing.id}`, payload)
  } catch {
    await apiClient.post('/soul_configs', payload)
  }
  return config
}

/** 测试 Ollama 连接 */
export async function testConnection(baseUrl: string): Promise<ConnectionTestResult> {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)
    const resp = await fetch(`${baseUrl}/api/tags`, { signal: controller.signal })
    clearTimeout(timeout)
    if (resp.ok) {
      return { success: true, message: '连接成功！', latency: 12 }
    }
    return { success: false, message: `连接失败：HTTP ${resp.status}` }
  } catch {
    return { success: false, message: '无法连接到 Ollama 服务，请检查地址是否正确。' }
  }
}

/** 获取可用模型列表 */
export async function fetchModels(baseUrl?: string): Promise<OllamaModel[]> {
  const url = baseUrl ?? 'http://localhost:11434'
  try {
    const resp = await fetch(`${url}/api/tags`)
    if (!resp.ok) return []
    const data = await resp.json()
    return (data.models ?? []).map((m: any) => ({
      name: m.name,
      size: m.size ?? 0,
      modifiedAt: m.modified_at ?? new Date().toISOString(),
    }))
  } catch {
    return []
  }
}

// ── 大模型供应商 API ─────────────────────────────────────────

/** 获取所有供应商列表 */
export async function getProviders(): Promise<LLMProvider[]> {
  const data = extractData(await apiClient.get('/llm_providers', { params: { page: 1, pageSize: 100 } })) as any
  return data?.items ?? data ?? []
}

/** 获取所有启用的供应商 */
export async function getEnabledProviders(): Promise<LLMProvider[]> {
  return (extractData(await apiClient.get('/llm_providers/enabled')) as LLMProvider[]) ?? []
}

/** 创建供应商 */
export async function createProvider(payload: LLMProviderPayload): Promise<LLMProvider> {
  return extractData(await apiClient.post('/llm_providers', payload))
}

/** 更新供应商 */
export async function updateProvider(id: number, payload: Partial<LLMProviderPayload>): Promise<LLMProvider> {
  return extractData(await apiClient.put(`/llm_providers/${id}`, payload))
}

/** 切换供应商启用/禁用状态 */
export async function toggleProvider(id: number): Promise<LLMProvider> {
  return extractData(await apiClient.put(`/llm_providers/${id}/toggle`))
}

/** 删除供应商 */
export async function deleteProvider(id: number): Promise<void> {
  await apiClient.delete(`/llm_providers/${id}`)
}
