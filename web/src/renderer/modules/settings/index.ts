/** 设置系统导出 */

// 组件
export { default as SettingsPanel } from './components/settings-panel'
export { OllamaSettings } from './components/ollama-settings'
export { AiSettings } from './components/ai-settings'
export { AppSettingsPanel } from './components/app-settings'
export { ShortcutSettings } from './components/shortcut-settings'
export { PrivacySettings } from './components/privacy-settings'
export { AboutSettings } from './components/about-settings'
export { SoulSettings } from './components/soul-settings'
export { PromptManager } from './components/prompt-manager'
export { PromptVersionHistory } from './components/prompt-version-history'
export { PromptDiff } from './components/prompt-diff'
export { DataManagement } from './components/data-management'
export type { ExportData } from './components/data-management'

// Hooks
export { useSettings } from './hooks/use-settings'

// Services
export {
  getSettings,
  saveSettings,
  getSoulConfig,
  saveSoulConfig,
  testConnection,
  fetchModels,
} from './services/settings-api'

// Types
export type {
  AppSettings,
  OllamaConfig,
  AiConfig,
  AppConfig,
  PrivacyConfig,
  ShortcutItem,
  SoulConfig,
  OllamaModel,
  ConnectionTestResult,
  RestartRequiredField,
  PersonalityPreset,
  SpeakingStyle,
  PromptConfig,
  PromptVersion,
  ABTestConfig,
} from './types/settings'

export { SPEAKING_STYLES, PERSONALITY_PRESETS } from './types/settings'

// 灵魂引导
export { SoulOnboard } from './components/soul-onboard'
export type { SoulOnboardData, SoulOnboardProps } from './types/soul-onboard'
