/**
 * 类型定义统一导出
 *
 * 命名规约：前端统一 camelCase，API 拦截器自动转换 snake_case ↔ camelCase
 * 字段对齐：所有类型与数据库表结构一一对应（camelCase 版本）
 */

// API 通用类型
export type {
  ApiResponse,
  PaginatedResponse,
  ApiErrorResponse,
  PaginationParams,
  SortParams,
} from './api'

// 通用类型
export type {
  Option,
  TreeNode,
  KeyValuePair,
  OperationResult,
  TimeRange,
  FileInfo,
  Point,
  Rect,
  ThemeMode,
  NetworkStatus,
} from './common'

// ─── 对话 ───
export interface Conversation {
  id: string
  title: string
  modelName: string
  messageCount: number
  lastMessageAt: string | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface ChatMessage {
  id: string
  conversationId: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  toolCalls: ToolCall[] | null
  toolCallId: string | null
  tokenCount: number
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface ToolCall {
  id: string
  name: string
  arguments: string
  result?: string
}

// ─── 日程 ───
export interface Schedule {
  id: string
  title: string
  description: string
  startTime: string
  endTime: string | null
  isAllDay: number
  reminderMinutes: number
  isReminded: number
  repeatType: number
  color: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 剪贴板 ───
export interface ClipboardItem {
  id: string
  content: string
  contentType: number
  isPinned: number
  sourceApp: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 代码片段 ───
export interface Snippet {
  id: string
  title: string
  content: string
  language: string
  useCount: number
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface SnippetTag {
  id: string
  snippetId: string
  tag: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 知识库 ───
export interface KnowledgeDocument {
  id: string
  filename: string
  fileType: string
  fileSize: number
  chunkCount: number
  status: number
  errorMessage: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 记忆 ───
export interface MemoryEntry {
  id: string
  conversationId: string | null
  summary: string
  tags: string[] | null
  importance: number
  qdrantPointId: string | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 技能 ───
export interface Skill {
  id: string
  name: string
  displayName: string
  description: string
  version: string
  source: string
  triggerWords: string[] | null
  dependencies: string[] | null
  isEnabled: number
  config: Record<string, unknown> | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface SkillStats {
  id: string
  skillId: string
  callCount: number
  successCount: number
  failCount: number
  avgDurationMs: number
  lastCalledAt: string | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 工作流 ───
export interface Workflow {
  id: string
  name: string
  description: string
  dagJson: string
  triggerType: number
  cronExpr: string
  eventTrigger: string
  isEnabled: number
  version: number
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface WorkflowRun {
  id: string
  workflowId: string
  status: number
  triggerType: number
  inputJson: string | null
  outputJson: string | null
  errorMessage: string
  startedAt: string | null
  finishedAt: string | null
  durationMs: number
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface WorkflowStepRun {
  id: string
  runId: string
  stepName: string
  stepType: string
  status: number
  inputJson: string | null
  outputJson: string | null
  errorMessage: string
  startedAt: string | null
  finishedAt: string | null
  durationMs: number
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 子代理 ───
export interface SubAgent {
  id: string
  taskName: string
  status: 'running' | 'paused' | 'completed' | 'failed'
  startedAt: string
  currentStep?: string
}

// ─── 工具 ───
export interface Tool {
  id: string
  name: string
  displayName: string
  description: string
  module: string
  jsonSchema: string
  isEnabled: number
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface ToolStats {
  id: string
  toolId: string
  callCount: number
  successCount: number
  failCount: number
  avgDurationMs: number
  lastCalledAt: string | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 宠物 ───
export interface PetAttributes {
  id: string
  hunger: number
  clean: number
  mood: number
  health: number
  intimacy: number
  level: number
  exp: number
  lastActiveAt: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface PetInteraction {
  id: string
  interactionType: number
  effectJson: Record<string, unknown> | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 性能监控 ───
export interface PerformanceMetric {
  id: string
  cpuPercent: number
  memoryPercent: number
  memoryUsedMb: number
  diskPercent: number
  diskUsedGb: number
  gpuPercent: number | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 通知 ───
export type NotificationType =
  | 'schedule'
  | 'workflow'
  | 'subagent'
  | 'skill_suggest'
  | 'system_alert'

export interface Notification {
  id: string
  eventId: string
  type: NotificationType
  title: string
  message: string
  isRead: number
  actionUrl: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 设置 ───
export interface Settings {
  ollama: {
    host: string
    chatModel: string
    embeddingModel: string
    visionModel: string
  }
  ai: {
    temperature: number
    maxTokens: number
    topP: number
    frequencyPenalty: number
    aiAvatar: string
    systemPrompt: string
  }
  app: {
    language: string
    autoStart: boolean
    startMinimized: boolean
    closeAction: 'exit' | 'minimize'
  }
  hotkeys: Record<string, string>
  privacy: {
    encryptData: boolean
    logLevel: 'debug' | 'info' | 'warn' | 'error'
    anonymousStats: boolean
  }
}

// ─── 灵魂配置 ───
export interface SoulConfig {
  id: string
  name: string
  avatarUrl: string
  personality: string[]
  speakingStyle: string
  background: string
  systemPrompt: string
  isActive: number
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── Prompt 版本管理 ───
export interface Prompt {
  id: string
  name: string
  content: string
  version: number
  isActive: number
  description: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── AI 反馈 ───
export interface AiFeedback {
  id: string
  conversationId: string | null
  question: string
  answer: string
  feedbackType: number
  reasonTags: string[] | null
  reasonText: string
  traceId: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 意图 ───
export interface Intent {
  id: string
  name: string
  description: string
  triggerTexts: string[]
  targetModule: string
  metadata: Record<string, unknown> | null
  isEnabled: number
  qdrantPointId: string | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface IntentUsage {
  id: string
  intentId: string
  hitCount: number
  avgConfidence: number
  lastHitAt: string | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 命令 ───
export interface Command {
  id: string
  name: string
  displayName: string
  description: string
  shortcutKey: string
  module: string
  commandType: number
  isEnabled: number
  isDeleted: number
  createdAt: string
  updatedAt: string
}

export interface CommandUsage {
  id: string
  commandId: string
  useCount: number
  lastUsedAt: string | null
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 备份 ───
export interface BackupRecord {
  id: string
  backupType: number
  filePath: string
  fileSize: number
  status: number
  errorMessage: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── 行为日志 ───
export interface ActionLog {
  id: string
  module: string
  action: string
  paramsSummary: string
  sessionId: string
  isDeleted: number
  createdAt: string
  updatedAt: string
}

// ─── Electron API 类型 ───
declare global {
  interface Window {
    electronAPI: {
      window: {
        minimize: () => Promise<void>
        maximize: () => Promise<void>
        close: () => Promise<void>
        isMaximized: () => Promise<boolean>
      }
      app: {
        getVersion: () => Promise<string>
      }
      pet: {
        show: () => Promise<void>
        hide: () => Promise<void>
        toggle: () => Promise<void>
        getAttributes: () => Promise<PetAttributes | { error: string; message: string }>
        onScreenshotUpdate: (callback: (data: string) => void) => void
        onVisibilityChange: (callback: (visible: boolean) => void) => void
        sendScreenshot: (data: string) => void
      }
    }
  }
}
