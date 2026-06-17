/** 专家团工作流类型定义 — camelCase 匹配后端 API */

// ─── 专家（独立实体）─────────────────────────────────────

/** 专家 */
export interface Expert {
  id: number
  memberName: string
  memberRole: string
  avatar: string
  systemPrompt: string
  modelName: string
  providerId?: number | null
  temperature: number
  maxTokens: number
  toolsJson: Record<string, unknown>[] | null
  isEnabled: number
  createdAt: string | null
  updatedAt: string | null
}

/** 创建/编辑专家表单 */
export interface ExpertFormInput {
  memberName: string
  memberRole: string
  avatar?: string
  systemPrompt: string
  modelName?: string
  providerId?: number | null
  temperature?: number
  maxTokens?: number
  toolsJson?: Record<string, unknown>[]
  isEnabled?: number
}

// ─── 专家技能绑定 ────────────────────────────────────────

/** 专家技能绑定 */
export interface ExpertSkill {
  id: number
  expertId: number
  skillId: number
  skillName: string
  skillDisplayName: string
  skillDescription: string
  priority: number
  configOverride: Record<string, unknown> | null
  isEnabled: number
  createdAt: string | null
  updatedAt: string | null
}

/** 创建专家技能绑定 */
export interface ExpertSkillCreate {
  skillId: number
  priority?: number
  configOverride?: Record<string, unknown>
  isEnabled?: number
}

/** 更新专家技能绑定 */
export interface ExpertSkillUpdate {
  priority?: number
  configOverride?: Record<string, unknown>
  isEnabled?: number
}

// ─── 专家团 ──────────────────────────────────────────────

/** 专家团 */
export interface ExpertTeam {
  id: number
  teamName: string
  description: string
  icon: string
  category: string
  leaderId: number
  orchestratorPrompt: string
  synthesizerPrompt: string
  maxRounds: number
  isEnabled: number
  version: number
  configJson: Record<string, unknown> | null
  leader: Expert | null
  experts: Expert[]
  createdAt: string | null
  updatedAt: string | null
}

/** 创建专家团表单 */
export interface ExpertTeamFormInput {
  teamName: string
  description?: string
  icon?: string
  category?: string
  leaderId?: number
  orchestratorPrompt?: string
  synthesizerPrompt?: string
  maxRounds?: number
  configJson?: Record<string, unknown>
  expertIds: number[]
}

/** 更新专家团表单 */
export interface ExpertTeamUpdateInput {
  teamName?: string
  description?: string
  icon?: string
  category?: string
  leaderId?: number
  orchestratorPrompt?: string
  synthesizerPrompt?: string
  maxRounds?: number
  isEnabled?: number
  configJson?: Record<string, unknown>
  expertIds?: number[]
}

/** 绑定专家到专家团 */
export interface ExpertTeamBindExperts {
  expertIds: number[]
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
  experts: ExpertFormInput[]
  orchestratorPrompt: string
  synthesizerPrompt: string
  maxRounds: number
}

// ─── 状态映射 ────────────────────────────────────────────

// ─── WebSocket 实时事件类型 ───────────────────────────────

/** 专家状态事件 */
export interface ExpertStatusEvent {
  expertName: string
  expertRole: string
  avatar?: string
  status: 'running' | 'done' | 'failed'
  round: number
  runId: number
  teamId?: number
  durationMs?: number
  error?: string
}

/** 专家推理事件 */
export interface ExpertThinkingEvent {
  expertName: string
  expertRole: string
  avatar?: string
  round: number
  content: string
  runId: number
  teamId?: number
  durationMs?: number
}

/** 专家进度事件 */
export interface ExpertProgressEvent {
  status: 'running' | 'completed' | 'failed'
  runId: number
  teamId?: number
  output?: string
}

/** 实时执行中的专家状态 */
export interface LiveExpertState {
  name: string
  role: string
  avatar: string
  status: 'idle' | 'running' | 'done' | 'failed'
  currentRound: number
  thinking: string
  durationMs: number
}

/** 实时执行状态 */
export interface LiveExecutionState {
  runId: number | null
  status: 'idle' | 'orchestrating' | 'discussing' | 'synthesizing' | 'completed' | 'failed'
  currentRound: number
  maxRounds: number
  experts: Map<string, LiveExpertState>
  thinkingLog: ExpertThinkingEvent[]
  output: string
}

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
