/** 设置系统类型定义 */

/** Ollama 配置 */
export interface OllamaConfig {
  /** 服务地址 */
  baseUrl: string
  /** 对话模型 */
  chatModel: string
  /** 向量嵌入模型 */
  embedModel: string
  /** 视觉模型 */
  visionModel: string
}

/** AI 参数配置 */
export interface AiConfig {
  /** 温度 0-2 */
  temperature: number
  /** 最大 Token 1-8192 */
  maxTokens: number
  /** Top-P 0-1 */
  topP: number
  /** 系统提示词 */
  systemPrompt: string
}

/** 应用配置 */
export interface AppConfig {
  /** 语言 */
  language: string
  /** 开机自启 */
  autoLaunch: boolean
  /** 最小化到托盘 */
  minimizeToTray: boolean
  /** 关闭行为 */
  closeBehavior: 'exit' | 'minimize'
}

/** 隐私安全配置 */
export interface PrivacyConfig {
  /** 数据加密 */
  encryptData: boolean
  /** 日志级别 */
  logLevel: 'debug' | 'info' | 'warn' | 'error'
  /** 匿名统计 */
  anonymousStats: boolean
}

/** 快捷键映射 */
export interface ShortcutItem {
  /** 功能名称 */
  action: string
  /** 功能描述 */
  description: string
  /** 快捷键组合 */
  keys: string
  /** 是否可编辑 */
  editable: boolean
}

/** 全局应用设置 */
export interface AppSettings {
  ollama: OllamaConfig
  ai: AiConfig
  app: AppConfig
  privacy: PrivacyConfig
}

/** 灵魂配置 */
export interface SoulConfig {
  /** 助手名称 */
  name: string
  /** 头像 URL */
  avatar: string
  /** 性格标签 */
  personality: string[]
  /** 说话风格 */
  speakingStyle: string
  /** 情感倾向 0-100 */
  emotionalTendency: number
  /** 背景故事 */
  backgroundStory: string
}

/** Ollama 模型信息 */
export interface OllamaModel {
  /** 模型名称 */
  name: string
  /** 模型大小（字节） */
  size: number
  /** 修改时间 */
  modifiedAt: string
}

/** 连接测试结果 */
export interface ConnectionTestResult {
  success: boolean
  message: string
  latency?: number
}

/** 设置更新事件（标记需重启的配置） */
export type RestartRequiredField = 'ollama.baseUrl' | 'app.language' | 'app.autoLaunch'

/** 性格标签预设（带颜色） */
export interface PersonalityPreset {
  label: string
  color: string
}

/** 说话风格预设 */
export const SPEAKING_STYLES = [
  '温柔亲切',
  '活泼俏皮',
  '沉稳专业',
  '幽默风趣',
  '简洁干练',
  '文艺诗意',
  '毒舌傲娇',
  '治愈暖心',
] as const

export type SpeakingStyle = (typeof SPEAKING_STYLES)[number]

// ── 大模型供应商 + 模型（方案 A: 两表分离）────────────────────

/** 供应商类型 */
export type ProviderType = 'openai' | 'claude' | 'deepseek' | 'ollama' | 'qwen' | 'xiaomi' | 'zhipu' | 'moonshot' | 'agnes' | 'custom'

/** 模型配置（独立实体，从 llm_model 表读取） */
export interface LLMModel {
  id: number
  providerId: number
  modelName: string       // 实际调用名，如 gpt-4o
  displayName: string     // 显示名，如 GPT-4o
  contextLength: number   // 上下文窗口
  maxTokens: number       // 默认最大输出 token
  temperature: number     // 温度 0-2
  capabilities: {
    supportsVision?: boolean
    supportsTools?: boolean
    supportsStreaming?: boolean
    supportsReasoning?: boolean
    reasoningFormat?: string
  }
  isEnabled: number       // 1=启用 0=禁用
  sortOrder: number       // 排序
  remark: string
  createdAt?: string
  updatedAt?: string
}

/** 创建模型参数 */
export interface LLMModelPayload {
  modelName: string
  displayName?: string
  contextLength?: number
  maxTokens?: number
  temperature?: number
  capabilities?: {
    supportsVision?: boolean
    supportsTools?: boolean
    supportsStreaming?: boolean
    supportsReasoning?: boolean
    reasoningFormat?: string
  }
  isEnabled?: number
  sortOrder?: number
  remark?: string
}

/** 大模型供应商配置 */
export interface LLMProvider {
  id: number
  name: string
  providerType: ProviderType
  baseUrl: string
  apiKey: string
  models: LLMModel[]       // 关联的模型列表
  isEnabled: number
  isDefault: number
  description: string
  createdAt?: string
  updatedAt?: string
}

/** 创建/更新供应商参数 */
export interface LLMProviderPayload {
  name: string
  providerType: ProviderType
  baseUrl: string
  apiKey: string
  models?: LLMModelPayload[]  // 附带模型列表
  isEnabled?: number
  isDefault?: number
  description?: string
}

/** 供应商预设配置 */
export const PROVIDER_PRESETS: Record<ProviderType, { name: string; baseUrl: string; placeholder: string }> = {
  openai: { name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', placeholder: 'sk-...' },
  claude: { name: 'Claude', baseUrl: 'https://api.anthropic.com/v1', placeholder: 'sk-ant-...' },
  deepseek: { name: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', placeholder: 'sk-...' },
  ollama: { name: 'Ollama', baseUrl: 'http://localhost:11434', placeholder: '无需 Key' },
  qwen: { name: '通义千问', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', placeholder: 'sk-...' },
  xiaomi: { name: '小米 MiMo', baseUrl: 'https://api.xiaomimimo.com/v1', placeholder: 'sk-...' },
  zhipu: { name: '智谱 AI', baseUrl: 'https://open.bigmodel.cn/api/paas/v4', placeholder: '...' },
  moonshot: { name: '月之暗面', baseUrl: 'https://api.moonshot.cn/v1', placeholder: 'sk-...' },
  agnes: { name: 'Agnes AI', baseUrl: 'https://apihub.agnes-ai.com/v1', placeholder: '输入 API Key' },
  custom: { name: '自定义', baseUrl: '', placeholder: '输入 API Key' },
}

/** Prompt 版本 */
export interface PromptVersion {
  /** 版本 ID */
  id: string
  /** 版本号 */
  version: number
  /** Prompt 内容 */
  content: string
  /** 创建时间 (timestamp ms) */
  createdAt: number
  /** 创建者 */
  createdBy: string
  /** 是否为激活版本 */
  isActive: boolean
}

/** A/B 测试配置 */
export interface ABTestConfig {
  /** 是否启用 */
  enabled: boolean
  /** 测试变体 */
  variants: { versionId: string; weight: number }[]
}

/** Prompt 配置 */
export interface PromptConfig {
  /** Prompt ID */
  id: string
  /** 名称 */
  name: string
  /** 描述 */
  description: string
  /** 版本列表 */
  versions: PromptVersion[]
  /** 激活版本 ID */
  activeVersionId: string
  /** A/B 测试配置 */
  abTest?: ABTestConfig
}

/** 性格标签预设列表 */
export const PERSONALITY_PRESETS: PersonalityPreset[] = [
  { label: '温柔', color: '#ff85c0' },
  { label: '活泼', color: '#ff7a45' },
  { label: '聪明', color: '#597ef7' },
  { label: '幽默', color: '#ffc53d' },
  { label: '认真', color: '#73d13d' },
  { label: '体贴', color: '#ff85c0' },
  { label: '博学', color: '#36cfc9' },
  { label: '元气', color: '#ff4d4f' },
  { label: '高冷', color: '#8c8c8c' },
  { label: '呆萌', color: '#b37feb' },
  { label: '傲娇', color: '#f759ab' },
  { label: '可靠', color: '#40a9ff' },
  { label: '毒舌', color: '#ff4d4f' },
  { label: '治愈', color: '#95de64' },
  { label: '文艺', color: '#597ef7' },
  { label: '热血', color: '#ff7a45' },
]
