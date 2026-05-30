/** 专家团工作流类型定义 — camelCase 匹配后端 API */

// ─── 专家成员 ────────────────────────────────────────────

/** 专家成员 */
export interface ExpertMember {
  id: number
  teamId: number
  name: string
  role: string
  avatar: string
  systemPrompt: string
  modelName: string
  temperature: number
  maxTokens: number
  toolsJson: Record<string, unknown>[] | null
  sortOrder: number
  enabled: number
  createdAt: string | null
  updatedAt: string | null
}

/** 创建专家成员表单 */
export interface ExpertMemberFormInput {
  name: string
  role: string
  avatar?: string
  systemPrompt: string
  modelName?: string
  temperature?: number
  maxTokens?: number
  toolsJson?: Record<string, unknown>[]
  enabled?: number
}

// ─── 专家团 ──────────────────────────────────────────────

/** 专家团 */
export interface ExpertTeam {
  id: number
  name: string
  description: string
  icon: string
  category: string
  orchestratorPrompt: string
  synthesizerPrompt: string
  maxRounds: number
  enabled: number
  version: number
  configJson: Record<string, unknown> | null
  members: ExpertMember[]
  createdAt: string | null
  updatedAt: string | null
}

/** 创建专家团表单 */
export interface ExpertTeamFormInput {
  name: string
  description?: string
  icon?: string
  category?: string
  orchestratorPrompt?: string
  synthesizerPrompt?: string
  maxRounds?: number
  configJson?: Record<string, unknown>
  members: ExpertMemberFormInput[]
}

/** 更新专家团表单 */
export interface ExpertTeamUpdateInput {
  name?: string
  description?: string
  icon?: string
  category?: string
  orchestratorPrompt?: string
  synthesizerPrompt?: string
  maxRounds?: number
  enabled?: number
  configJson?: Record<string, unknown>
}

// ─── 讨论消息 ────────────────────────────────────────────

/** 讨论消息 */
export interface DiscussionMessage {
  round: number
  expertName: string
  expertRole: string
  content: string
  timestamp: string
}

// ─── 运行记录 ────────────────────────────────────────────

/** 运行状态 */
export type ExpertRunStatus = 0 | 1 | 2 | 3 | 4 // 待执行 | 运行中 | 已完成 | 失败 | 已取消

/** 运行记录 */
export interface ExpertTeamRun {
  id: number
  teamId: number
  teamName?: string
  status: ExpertRunStatus
  triggerType: number
  inputText: string
  outputText: string
  discussionJson: DiscussionMessage[] | null
  errorMessage: string
  roundCount: number
  tokenUsage: number
  startedAt: string | null
  finishedAt: string | null
  durationMs: number
  createdAt: string | null
}

/** 执行请求 */
export interface ExpertTeamExecuteInput {
  inputText: string
  maxRounds?: number
}

/** 执行结果 */
export interface ExpertTeamExecuteResult {
  runId: number
  status: number
  output: string
  discussion: DiscussionMessage[]
  rounds: number
  tokenUsage: number
  durationMs: number
}

// ─── 预设模板 ────────────────────────────────────────────

/** 专家团模板 */
export interface ExpertTeamTemplate {
  id: string
  name: string
  description: string
  icon: string
  category: string
  members: ExpertMemberFormInput[]
  orchestratorPrompt: string
  synthesizerPrompt: string
  maxRounds: number
}

// ─── 状态映射 ────────────────────────────────────────────

export const EXPERT_RUN_STATUS_MAP: Record<
  ExpertRunStatus,
  { label: string; color: string }
> = {
  0: { label: '待执行', color: 'default' },
  1: { label: '运行中', color: 'processing' },
  2: { label: '已完成', color: 'success' },
  3: { label: '失败', color: 'error' },
  4: { label: '已取消', color: 'warning' },
}

/** 专家角色预设颜色 */
export const EXPERT_ROLE_COLORS: Record<string, string> = {
  '架构师': '#1890ff',
  '测试专家': '#52c41a',
  '产品经理': '#faad14',
  '设计师': '#eb2f96',
  '安全专家': '#f5222d',
  '数据专家': '#722ed1',
  '运维专家': '#13c2c2',
  '前端专家': '#2f54eb',
  '后端专家': '#fa8c16',
  'AI 专家': '#a0d911',
}

/** 获取角色颜色 */
export function getExpertRoleColor(role: string): string {
  return EXPERT_ROLE_COLORS[role] || '#8c8c8c'
}
