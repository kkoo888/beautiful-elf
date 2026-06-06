/**
 * 设置管理 Hook
 * 提供设置读写、即时保存、重启提示等能力
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  getSettings,
  saveSettings,
  getSoulConfig,
  saveSoulConfig,
  testConnection,
  fetchModels,
} from '../services/settings-api'
import type {
  AppSettings,
  SoulConfig,
  OllamaModel,
  ConnectionTestResult,
  RestartRequiredField,
} from '../types/settings'

/** 需要重启的字段列表 */
const RESTART_FIELDS: RestartRequiredField[] = ['ollama.baseUrl', 'app.language', 'app.autoLaunch']

interface UseSettingsReturn {
  /** 应用设置 */
  settings: AppSettings
  /** 灵魂配置 */
  soul: SoulConfig
  /** 是否加载中 */
  isLoading: boolean
  /** 更新设置（即时保存） */
  updateSettings: (partial: Partial<AppSettings>) => void
  /** 更新灵魂配置（即时保存） */
  updateSoul: (partial: Partial<SoulConfig>) => void
  /** 测试 Ollama 连接 */
  testOllamaConnection: () => Promise<ConnectionTestResult>
  /** 获取模型列表 */
  loadModels: () => Promise<OllamaModel[]>
  /** 模型列表 */
  models: OllamaModel[]
  /** 需要重启提示 */
  restartHint: string | null
  /** 清除重启提示 */
  clearRestartHint: () => void
}

export function useSettings(): UseSettingsReturn {
  const [settings, setSettings] = useState<AppSettings>({
    ollama: { baseUrl: 'http://localhost:11434', chatModel: '', embedModel: '', visionModel: '' },
    ai: { temperature: 0.7, maxTokens: 2048, topP: 0.9, systemPrompt: '' },
    app: { language: 'zh-CN', autoLaunch: false, minimizeToTray: true, closeBehavior: 'minimize' },
    privacy: { encryptData: false, logLevel: 'info', anonymousStats: true },
  })
  const [soul, setSoul] = useState<SoulConfig>({
    name: '',
    avatar: '',
    personality: [],
    speakingStyle: '温柔亲切',
    emotionalTendency: 60,
    backgroundStory: '',
  })
  const [models, setModels] = useState<OllamaModel[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [restartHint, setRestartHint] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /** 加载初始数据 */
  useEffect(() => {
    void (async () => {
      try {
        const [s, sc] = await Promise.all([getSettings(), getSoulConfig()])
        setSettings(s)
        setSoul(sc)
      } finally {
        setIsLoading(false)
      }
    })()
  }, [])

  /** 检查是否涉及需重启字段 */
  const checkRestartRequired = useCallback(
    (partial: Record<string, unknown>, prefix = ''): void => {
      for (const key of Object.keys(partial)) {
        const fieldPath = prefix ? `${prefix}.${key}` : key
        if (RESTART_FIELDS.includes(fieldPath as RestartRequiredField)) {
          setRestartHint(`"${fieldPath}" 的修改需要重启应用后生效`)
          return
        }
        // 递归检查嵌套对象
        const val = partial[key]
        if (val && typeof val === 'object' && !Array.isArray(val)) {
          checkRestartRequired(val as Record<string, unknown>, fieldPath)
        }
      }
    },
    []
  )

  /** 更新设置（debounce 保存） */
  const updateSettings = useCallback(
    (partial: Partial<AppSettings>) => {
      setSettings((prev) => {
        const merged: AppSettings = {
          ollama: { ...prev.ollama, ...partial.ollama },
          ai: { ...prev.ai, ...partial.ai },
          app: { ...prev.app, ...partial.app },
          privacy: { ...prev.privacy, ...partial.privacy },
        }
        // debounce 保存
        if (debounceRef.current) clearTimeout(debounceRef.current)
        debounceRef.current = setTimeout(() => {
          void saveSettings(merged)
        }, 300)
        return merged
      })
      checkRestartRequired(partial as Record<string, unknown>)
    },
    [checkRestartRequired]
  )

  /** 更新灵魂配置（debounce 保存） */
  const updateSoul = useCallback((partial: Partial<SoulConfig>) => {
    setSoul((prev) => {
      const merged = { ...prev, ...partial }
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        void saveSoulConfig(merged)
      }, 300)
      return merged
    })
  }, [])

  /** 测试 Ollama 连接 */
  const testOllamaConnection = useCallback(async (): Promise<ConnectionTestResult> => {
    return testConnection(settings.ollama.baseUrl)
  }, [settings.ollama.baseUrl])

  /** 加载模型列表 */
  const loadModels = useCallback(async (): Promise<OllamaModel[]> => {
    const list = await fetchModels(settings.ollama.baseUrl)
    setModels(list)
    return list
  }, [settings.ollama.baseUrl])

  const clearRestartHint = useCallback(() => setRestartHint(null), [])

  return useMemo(
    () => ({
      settings,
      soul,
      isLoading,
      updateSettings,
      updateSoul,
      testOllamaConnection,
      loadModels,
      models,
      restartHint,
      clearRestartHint,
    }),
    [
      settings,
      soul,
      isLoading,
      updateSettings,
      updateSoul,
      testOllamaConnection,
      loadModels,
      models,
      restartHint,
      clearRestartHint,
    ]
  )
}
