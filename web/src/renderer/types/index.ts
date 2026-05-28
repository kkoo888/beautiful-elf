/**
 * 类型定义统一导出
 */

// API 通用类型
export type {
  ApiResponse,
  PaginatedResponse,
  ApiErrorResponse,
  PaginationParams,
  SortParams
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
  NetworkStatus
} from './common'

// ─── 对话 ───
export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: number
  tool_calls?: ToolCall[]
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
  description?: string
  start_time: string
  end_time: string
  is_all_day: boolean
  reminder_minutes: number
  color?: string
  repeat: 'none' | 'daily' | 'weekly' | 'monthly'
  deleted: number
  created_at: string
  updated_at: string
}

// ─── 剪贴板 ───
export interface ClipboardItem {
  id: string
  content: string
  type: 'text' | 'image' | 'file'
  pinned: boolean
  created_at: number
}

// ─── 代码片段 ───
export interface Snippet {
  id: string
  title: string
  code: string
  language: string
  tags: string[]
  use_count: number
  created_at: string
  updated_at: string
}

// ─── 知识库 ───
export interface KnowledgeDocument {
  id: string
  filename: string
  file_type: string
  chunk_count: number
  deleted: number
  created_at: string
}

// ─── 记忆 ───
export interface MemoryEntry {
  id: string
  content: string
  conversation_id: string
  created_at: string
}

// ─── 技能 ───
export interface Skill {
  id: string
  name: string
  description: string
  version: string
  enabled: boolean
  trigger_words: string[]
  created_at: string
}

// ─── 工作流 ───
export interface Workflow {
  id: string
  name: string
  description: string
  dag_json: string
  created_at: string
}

export interface WorkflowRun {
  id: string
  workflow_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string
  completed_at?: string
}

// ─── 子代理 ───
export interface SubAgent {
  id: string
  task_name: string
  status: 'running' | 'paused' | 'completed' | 'failed'
  started_at: string
  current_step?: string
}

// ─── 工具 ───
export interface Tool {
  id: string
  name: string
  description: string
  json_schema: string
  module: string
  created_at: string
}

export interface ToolStats {
  tool_id: string
  call_count: number
  success_rate: number
  avg_duration_ms: number
}

// ─── 宠物 ───
export interface PetAttributes {
  hunger: number
  clean: number
  mood: number
  health: number
  intimacy: number
  level: number
}

// ─── 性能监控 ───
export interface PerformanceMetrics {
  cpu: number
  memory: number
  disk: number
  timestamp: number
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
  event_id?: string
  type: NotificationType
  title: string
  message: string
  read: boolean
  created_at: string
  action_url?: string
}

// ─── 设置 ───
export interface Settings {
  ollama: {
    host: string
    chat_model: string
    embedding_model: string
    vision_model: string
  }
  ai: {
    temperature: number
    max_tokens: number
    top_p: number
    frequency_penalty: number
    ai_avatar: string
    system_prompt: string
  }
  app: {
    language: string
    auto_start: boolean
    start_minimized: boolean
    close_action: 'exit' | 'minimize'
  }
  hotkeys: Record<string, string>
  privacy: {
    encrypt_data: boolean
    log_level: 'debug' | 'info' | 'warn' | 'error'
    anonymous_stats: boolean
  }
}

// ─── 灵魂配置 ───
export interface SoulConfig {
  id: string
  name: string
  avatar: string
  personality: string[]
  speaking_style: string
  emotion: string
  background: string
  rules: string[]
}

// ─── 命令 ───
export interface Command {
  id: string
  name: string
  keywords: string[]
  icon?: string
  module: string
  action: () => void
  use_count: number
  last_used_at?: number
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
    }
  }
}
