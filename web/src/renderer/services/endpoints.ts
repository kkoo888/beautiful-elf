/**
 * API 端点常量集中管理
 * 按模块分组，方便后端联调和维护
 *
 * ⚠️ 注意：apiClient.baseURL 已包含 /api/v1，此处路径不要重复加前缀
 */

// ─── 聊天 ───
export const CHAT_ENDPOINTS = {
  CONVERSATIONS: `/conversations`,
  CONVERSATION: (id: string) => `/conversations/${id}`,
  MESSAGES: `/messages`,
  CHAT: (conversationId: string) => `/conversations/${conversationId}/chat`,
} as const

// ─── 知识库 ───
export const KNOWLEDGE_ENDPOINTS = {
  DOCUMENTS: `/knowledge/documents`,
  DOCUMENT: (id: string) => `/knowledge/documents/${id}`,
  SEARCH: `/knowledge/search`,
} as const

// ─── 记忆 ───
export const MEMORY_ENDPOINTS = {
  LIST: `/memories`,
  CREATE: `/memories`,
  DETAIL: (id: string) => `/memories/${id}`,
  SEARCH: `/memories/search`,
} as const

// ─── 日程 ───
export const SCHEDULE_ENDPOINTS = {
  LIST: `/schedules`,
  CREATE: `/schedules`,
  DETAIL: (id: string) => `/schedules/${id}`,
  UPDATE: (id: string) => `/schedules/${id}`,
  DELETE: (id: string) => `/schedules/${id}`,
} as const

// ─── 技能 ───
export const SKILLS_ENDPOINTS = {
  LIST: `/skills`,
  DETAIL: (id: string) => `/skills/${id}`,
  EXECUTE: (id: string) => `/skills/${id}/execute`,
} as const

// ─── 工具 ───
export const TOOLS_ENDPOINTS = {
  LIST: `/tools`,
  DETAIL: (id: string) => `/tools/${id}`,
  EXECUTE: (id: string) => `/tools/${id}/execute`,
} as const

// ─── 通知 ───
export const NOTIFICATION_ENDPOINTS = {
  LIST: `/notifications`,
  MARK_READ: (id: string) => `/notifications/${id}/read`,
  MARK_ALL_READ: `/notifications/read-all`,
} as const

// ─── 设置 ───
export const SETTINGS_ENDPOINTS = {
  GET: `/settings`,
  UPDATE: `/settings`,
} as const

// ─── 翻译 ───
export const TRANSLATE_ENDPOINTS = {
  TRANSLATE: `/translate`,
  LANGUAGES: `/translate/languages`,
} as const

// ─── OCR ───
export const OCR_ENDPOINTS = {
  RECOGNIZE: `/ocr/recognize`,
} as const

// ─── 意图 ───
export const INTENT_ENDPOINTS = {
  LIST: `/intents`,
  CREATE: `/intents`,
  DETAIL: (id: string) => `/intents/${id}`,
  UPDATE: (id: string) => `/intents/${id}`,
  DELETE: (id: string) => `/intents/${id}`,
  ENABLE: (id: string) => `/intents/${id}/enable`,
  DISABLE: (id: string) => `/intents/${id}/disable`,
  SYNC: `/intents/sync`,
  MATCH_TEST: `/intents/match/test`,
} as const

// ─── 工作流 ───
export const WORKFLOW_ENDPOINTS = {
  LIST: `/workflows`,
  CREATE: `/workflows`,
  DETAIL: (id: string) => `/workflows/${id}`,
  UPDATE: (id: string) => `/workflows/${id}`,
  DELETE: (id: string) => `/workflows/${id}`,
  ENABLE: (id: string) => `/workflows/${id}/enable`,
  DISABLE: (id: string) => `/workflows/${id}/disable`,
  EXECUTE: (id: string) => `/workflows/${id}/execute`,
  RUNS: (id: string) => `/workflows/${id}/runs`,
} as const

// ─── 专家团 ───
export const EXPERT_TEAM_ENDPOINTS = {
  LIST: `/expert_teams`,
  CREATE: `/expert_teams`,
  DETAIL: (id: string) => `/expert_teams/${id}`,
  MEMBERS: (teamId: string) => `/expert_teams/${teamId}/members`,
  MEMBER_DETAIL: (memberId: string) => `/expert_teams/members/${memberId}`,
  EXECUTE: (id: string) => `/expert_teams/${id}/execute`,
  RUNS: (id: string) => `/expert_teams/${id}/runs`,
  RUNS_ALL: `/expert_teams/runs/all`,
  RUN_DETAIL: (runId: string) => `/expert_teams/runs/${runId}`,
} as const

// ─── 子代理 ───
export const SUBAGENT_ENDPOINTS = {
  LIST: `/subagents`,
  CREATE: `/subagents`,
  DETAIL: (id: string) => `/subagents/${id}`,
} as const

// ─── 备份 ───
export const BACKUP_ENDPOINTS = {
  CREATE: `/backup`,
  LIST: `/backup`,
  RESTORE: (id: string) => `/backup/${id}/restore`,
} as const

// ─── 系统 ───
export const SYSTEM_ENDPOINTS = {
  STATUS: `/system/status`,
  HEALTH: `/system/health`,
} as const

// ─── 大模型供应商 ───
export const LLM_PROVIDER_ENDPOINTS = {
  LIST: `/llm_providers`,
  ENABLED: `/llm_providers/enabled`,
  DETAIL: (id: string) => `/llm_providers/${id}`,
  TOGGLE: (id: string) => `/llm_providers/${id}/toggle`,
} as const

// ─── 认证 ───
export const AUTH_ENDPOINTS = {
  LOGIN: `/auth/login`,
  REGISTER: `/auth/register`,
  ME: `/auth/me`,
  CHANGE_PASSWORD: `/auth/change-password`,
  PROFILE: `/auth/profile`,
} as const
