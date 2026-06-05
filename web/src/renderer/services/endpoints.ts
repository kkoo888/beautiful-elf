import { API_PREFIX } from '@shared/constants'

/**
 * API 端点常量集中管理
 * 按模块分组，方便后端联调和维护
 */

// ─── 聊天 ───
export const CHAT_ENDPOINTS = {
  CONVERSATIONS: `${API_PREFIX}/conversations`,
  CONVERSATION: (id: string) => `${API_PREFIX}/conversations/${id}`,
  MESSAGES: `${API_PREFIX}/messages`,
  CHAT: (conversationId: string) => `${API_PREFIX}/conversations/${conversationId}/chat`,
} as const

// ─── 知识库 ───
export const KNOWLEDGE_ENDPOINTS = {
  DOCUMENTS: `${API_PREFIX}/knowledge/documents`,
  DOCUMENT: (id: string) => `${API_PREFIX}/knowledge/documents/${id}`,
  SEARCH: `${API_PREFIX}/knowledge/search`,
} as const

// ─── 记忆 ───
export const MEMORY_ENDPOINTS = {
  LIST: `${API_PREFIX}/memories`,
  CREATE: `${API_PREFIX}/memories`,
  DETAIL: (id: string) => `${API_PREFIX}/memories/${id}`,
  SEARCH: `${API_PREFIX}/memories/search`,
} as const

// ─── 日程 ───
export const SCHEDULE_ENDPOINTS = {
  LIST: `${API_PREFIX}/schedule`,
  CREATE: `${API_PREFIX}/schedule`,
  DETAIL: (id: string) => `${API_PREFIX}/schedule/${id}`,
  UPDATE: (id: string) => `${API_PREFIX}/schedule/${id}`,
  DELETE: (id: string) => `${API_PREFIX}/schedule/${id}`,
} as const

// ─── 技能 ───
export const SKILLS_ENDPOINTS = {
  LIST: `${API_PREFIX}/skills`,
  DETAIL: (id: string) => `${API_PREFIX}/skills/${id}`,
  EXECUTE: (id: string) => `${API_PREFIX}/skills/${id}/execute`,
} as const

// ─── 工具 ───
export const TOOLS_ENDPOINTS = {
  LIST: `${API_PREFIX}/tools`,
  DETAIL: (id: string) => `${API_PREFIX}/tools/${id}`,
  EXECUTE: (id: string) => `${API_PREFIX}/tools/${id}/execute`,
} as const

// ─── 通知 ───
export const NOTIFICATION_ENDPOINTS = {
  LIST: `${API_PREFIX}/notifications`,
  MARK_READ: (id: string) => `${API_PREFIX}/notifications/${id}/read`,
  MARK_ALL_READ: `${API_PREFIX}/notifications/read-all`,
} as const

// ─── 设置 ───
export const SETTINGS_ENDPOINTS = {
  GET: `${API_PREFIX}/settings`,
  UPDATE: `${API_PREFIX}/settings`,
} as const

// ─── 翻译 ───
export const TRANSLATE_ENDPOINTS = {
  TRANSLATE: `${API_PREFIX}/translate`,
  LANGUAGES: `${API_PREFIX}/translate/languages`,
} as const

// ─── OCR ───
export const OCR_ENDPOINTS = {
  RECOGNIZE: `${API_PREFIX}/ocr/recognize`,
} as const

// ─── 意图 ───
export const INTENT_ENDPOINTS = {
  LIST: `${API_PREFIX}/intents`,
  CREATE: `${API_PREFIX}/intents`,
  DETAIL: (id: string) => `${API_PREFIX}/intents/${id}`,
  UPDATE: (id: string) => `${API_PREFIX}/intents/${id}`,
  DELETE: (id: string) => `${API_PREFIX}/intents/${id}`,
  ENABLE: (id: string) => `${API_PREFIX}/intents/${id}/enable`,
  DISABLE: (id: string) => `${API_PREFIX}/intents/${id}/disable`,
  SYNC: `${API_PREFIX}/intents/sync`,
  MATCH_TEST: `${API_PREFIX}/intents/match/test`,
} as const

// ─── 工作流 ───
export const WORKFLOW_ENDPOINTS = {
  LIST: `${API_PREFIX}/workflows`,
  CREATE: `${API_PREFIX}/workflows`,
  DETAIL: (id: string) => `${API_PREFIX}/workflows/${id}`,
  UPDATE: (id: string) => `${API_PREFIX}/workflows/${id}`,
  DELETE: (id: string) => `${API_PREFIX}/workflows/${id}`,
  ENABLE: (id: string) => `${API_PREFIX}/workflows/${id}/enable`,
  DISABLE: (id: string) => `${API_PREFIX}/workflows/${id}/disable`,
  EXECUTE: (id: string) => `${API_PREFIX}/workflows/${id}/execute`,
  RUNS: (id: string) => `${API_PREFIX}/workflows/${id}/runs`,
} as const

// ─── 专家团 ───
export const EXPERT_TEAM_ENDPOINTS = {
  LIST: `${API_PREFIX}/expert_teams`,
  CREATE: `${API_PREFIX}/expert_teams`,
  DETAIL: (id: string) => `${API_PREFIX}/expert_teams/${id}`,
  MEMBERS: (teamId: string) => `${API_PREFIX}/expert_teams/${teamId}/members`,
  MEMBER_DETAIL: (memberId: string) => `${API_PREFIX}/expert_teams/members/${memberId}`,
  EXECUTE: (id: string) => `${API_PREFIX}/expert_teams/${id}/execute`,
  RUNS: (id: string) => `${API_PREFIX}/expert_teams/${id}/runs`,
  RUNS_ALL: `${API_PREFIX}/expert_teams/runs/all`,
  RUN_DETAIL: (runId: string) => `${API_PREFIX}/expert_teams/runs/${runId}`,
} as const

// ─── 子代理 ───
export const SUBAGENT_ENDPOINTS = {
  LIST: `${API_PREFIX}/subagents`,
  CREATE: `${API_PREFIX}/subagents`,
  DETAIL: (id: string) => `${API_PREFIX}/subagents/${id}`,
} as const

// ─── 备份 ───
export const BACKUP_ENDPOINTS = {
  CREATE: `${API_PREFIX}/backup`,
  LIST: `${API_PREFIX}/backup`,
  RESTORE: (id: string) => `${API_PREFIX}/backup/${id}/restore`,
} as const

// ─── 系统 ───
export const SYSTEM_ENDPOINTS = {
  STATUS: `${API_PREFIX}/system/status`,
  HEALTH: `${API_PREFIX}/system/health`,
} as const

// ─── 大模型供应商 ───
export const LLM_PROVIDER_ENDPOINTS = {
  LIST: `${API_PREFIX}/llm_providers`,
  ENABLED: `${API_PREFIX}/llm_providers/enabled`,
  DETAIL: (id: string) => `${API_PREFIX}/llm_providers/${id}`,
  TOGGLE: (id: string) => `${API_PREFIX}/llm_providers/${id}/toggle`,
} as const

// ─── 认证 ───
export const AUTH_ENDPOINTS = {
  LOGIN: `${API_PREFIX}/auth/login`,
  REGISTER: `${API_PREFIX}/auth/register`,
  ME: `${API_PREFIX}/auth/me`,
  CHANGE_PASSWORD: `${API_PREFIX}/auth/change-password`,
  PROFILE: `${API_PREFIX}/auth/profile`,
} as const
