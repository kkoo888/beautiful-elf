/** 设置系统 API 服务（对接后端 config + soul_config 接口） */

import { apiClient } from '@/services/api-client'
import type { AppSettings, SoulConfig, OllamaModel, ConnectionTestResult } from '../types/settings'

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

// ── 后端类型 ─────────────────────────────────────────────────

interface BackendConfigItem {
  id: number
  key: string
  value: string
  description: string
  created_at: string
  updated_at: string
}

interface BackendSoulConfig {
  id: number
  name: string
  avatar: string
  personality: string[]
  speaking_style: string
  emotional_tendency: number
  background_story: string
  is_active: number
  created_at: string
  updated_at: string
}

// ── 转换函数 ─────────────────────────────────────────────────

function toFrontendSoul(data: BackendSoulConfig): SoulConfig {
  return {
    name: data.name,
    avatar: data.avatar,
    personality: data.personality ?? [],
    speakingStyle: data.speaking_style ?? '温柔亲切',
    emotionalTendency: data.emotional_tendency ?? 60,
    backgroundStory: data.background_story ?? '',
  }
}

// ── API 函数 ─────────────────────────────────────────────────

/**
 * 获取应用设置
 * 后端用 key-value 存储，我们将整个 settings 存为 key="app_settings"
 */
export async function getSettings(): Promise<AppSettings> {
  try {
    const resp = await apiClient.get('/configs/app_settings')
    const item = (resp.data as any).data as BackendConfigItem
    if (item?.value) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(item.value) }
    }
  } catch {
    // key 不存在时返回默认值
  }
  return { ...DEFAULT_SETTINGS }
}

/**
 * 保存应用设置（部分更新）
 */
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
    // 尝试更新
    await apiClient.put('/configs/app_settings', {
      keyValue: jsonStr,
      description: '应用设置（JSON）',
    })
  } catch {
    // 不存在则创建
    await apiClient.post('/configs', {
      settingsKey: 'app_settings',
      keyValue: jsonStr,
      description: '应用设置（JSON）',
    })
  }

  return merged
}

/**
 * 获取灵魂配置
 */
export async function getSoulConfig(): Promise<SoulConfig> {
  try {
    const resp = await apiClient.get('/soul_configs/active')
    return toFrontendSoul((resp.data as any).data)
  } catch {
    return { ...DEFAULT_SOUL }
  }
}

/**
 * 保存灵魂配置
 * 先尝试查找已有的活跃配置来更新，没有则创建
 */
export async function saveSoulConfig(config: SoulConfig): Promise<SoulConfig> {
  try {
    // 尝试获取当前活跃配置
    const resp = await apiClient.get('/soul_configs/active')
    const existing = (resp.data as any).data as BackendSoulConfig
    await apiClient.put(`/soul_configs/${existing.id}`, {
      name: config.name,
      avatar: config.avatar,
      personality: config.personality,
      speaking_style: config.speakingStyle,
      emotional_tendency: config.emotionalTendency,
      background_story: config.backgroundStory,
    })
  } catch {
    // 没有活跃配置，创建新的
    await apiClient.post('/soul_configs', {
      name: config.name,
      avatar: config.avatar,
      personality: config.personality,
      speaking_style: config.speakingStyle,
      emotional_tendency: config.emotionalTendency,
      background_story: config.backgroundStory,
    })
  }
  return config
}

/**
 * 测试 Ollama 连接
 * 前端本地测试，不走后端
 */
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

/**
 * 获取可用模型列表
 */
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

import type { LLMProvider, LLMProviderPayload } from '../types/settings'

/**
 * 获取所有供应商列表
 */
export async function getProviders(): Promise<LLMProvider[]> {
  const resp = await apiClient.get('/llm_providers', { params: { page: 1, page_size: 500 } })
  const data = (resp.data as any).data
  // ok_page 格式: { items, total, page, pageSize }
  const items = data?.items ?? data ?? []
  return items.map(mapProviderFromBackend)
}

/**
 * 获取所有启用的供应商
 */
export async function getEnabledProviders(): Promise<LLMProvider[]> {
  const resp = await apiClient.get('/llm_providers/enabled')
  const items = (resp.data as any).data ?? []
  return items.map(mapProviderFromBackend)
}

/**
 * 创建供应商
 */
export async function createProvider(payload: LLMProviderPayload): Promise<LLMProvider> {
  const resp = await apiClient.post('/llm_providers', mapProviderToBackend(payload))
  return mapProviderFromBackend((resp.data as any).data)
}

/**
 * 更新供应商
 */
export async function updateProvider(id: number, payload: Partial<LLMProviderPayload>): Promise<LLMProvider> {
  const resp = await apiClient.put(`/llm_providers/${id}`, mapProviderToBackend(payload))
  return mapProviderFromBackend((resp.data as any).data)
}

/**
 * 切换供应商启用/禁用状态
 */
export async function toggleProvider(id: number): Promise<LLMProvider> {
  const resp = await apiClient.put(`/llm_providers/${id}/toggle`)
  return mapProviderFromBackend((resp.data as any).data)
}

/**
 * 删除供应商
 */
export async function deleteProvider(id: number): Promise<void> {
  await apiClient.delete(`/llm_providers/${id}`)
}

// ── 字段映射 ─────────────────────────────────────────────────

function mapProviderFromBackend(raw: any): LLMProvider {
  return {
    id: raw.id,
    name: raw.name,
    providerType: raw.provider_type,
    baseUrl: raw.base_url,
    apiKey: raw.api_key ?? '',
    models: (raw.models ?? []).map((m: any) => ({
      id: m.id ?? m.name,
      name: m.name,
      contextLength: m.context_length ?? 4096,
      supportsVision: m.supports_vision ?? false,
      supportsTools: m.supports_tools ?? false,
    })),
    enabled: raw.enabled ?? 1,
    isDefault: raw.is_default ?? 0,
    description: raw.description ?? '',
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  }
}

function mapProviderToBackend(payload: Partial<LLMProviderPayload>): Record<string, any> {
  const out: Record<string, any> = {}
  if (payload.name !== undefined) out.name = payload.name
  if (payload.providerType !== undefined) out.provider_type = payload.providerType
  if (payload.baseUrl !== undefined) out.base_url = payload.baseUrl
  if (payload.apiKey !== undefined) out.api_key = payload.apiKey
  if (payload.models !== undefined) {
    out.models = payload.models.map(m => ({
      id: m.id,
      name: m.name,
      context_length: m.contextLength ?? 4096,
      supports_vision: m.supportsVision ?? false,
      supports_tools: m.supportsTools ?? false,
    }))
  }
  if (payload.enabled !== undefined) out.enabled = payload.enabled
  if (payload.isDefault !== undefined) out.is_default = payload.isDefault
  if (payload.description !== undefined) out.description = payload.description
  return out
}
