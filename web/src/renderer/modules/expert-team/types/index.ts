/** 专家团工作流类型定义 */

// ─── 专家成员 ────────────────────────────────────────────

/** 专家成员 */
export interface ExpertMember {
  id: number
  team_id: number
  name: string
  role: string
  avatar: string
  system_prompt: string
  model_name: string
  temperature: number
  max_tokens: number
  tools_json: Record<string, unknown>[] | null
  sort_order: number
  enabled: number
  created_at: string | null
  updated_at: string | null
}

/** 创建专家成员表单 */
export interface ExpertMemberFormInput {
  name: string
  role: string
  avatar?: string
  system_prompt: string
  model_name?: string
  temperature?: number
  max_tokens?: number
  tools_json?: Record<string, unknown>[]
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
  orchestrator_prompt: string
  synthesizer_prompt: string
  max_rounds: number
  enabled: number
  version: number
  config_json: Record<string, unknown> | null
  members: ExpertMember[]
  created_at: string | null
  updated_at: string | null
}

/** 创建专家团表单 */
export interface ExpertTeamFormInput {
  name: string
  description?: string
  icon?: string
  category?: string
  orchestrator_prompt?: string
  synthesizer_prompt?: string
  max_rounds?: number
  config_json?: Record<string, unknown>
  members: ExpertMemberFormInput[]
}

/** 更新专家团表单 */
export interface ExpertTeamUpdateInput {
  name?: string
  description?: string
  icon?: string
  category?: string
  orchestrator_prompt?: string
  synthesizer_prompt?: string
  max_rounds?: number
  enabled?: number
  config_json?: Record<string, unknown>
}

// ─── 讨论消息 ────────────────────────────────────────────

/** 讨论消息 */
export interface DiscussionMessage {
  round: number
  expert_name: string
  expert_role: string
  content: string
  timestamp: string
}

// ─── 运行记录 ────────────────────────────────────────────

/** 运行状态 */
export type ExpertRunStatus = 0 | 1 | 2 | 3 | 4 // 待执行 | 运行中 | 已完成 | 失败 | 已取消

/** 运行记录 */
export interface ExpertTeamRun {
  id: number
  team_id: number
  team_name?: string
  status: ExpertRunStatus
  trigger_type: number
  input_text: string
  output_text: string
  discussion_json: DiscussionMessage[] | null
  error_message: string
  round_count: number
  token_usage: number
  started_at: string | null
  finished_at: string | null
  duration_ms: number
  created_at: string | null
}

/** 执行请求 */
export interface ExpertTeamExecuteInput {
  input_text: string
  max_rounds?: number
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
  orchestrator_prompt: string
  synthesizer_prompt: string
  max_rounds: number
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
