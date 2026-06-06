/** 子代理模块类型定义 */

/** 子代理状态 */
export type SubagentStatus = 'idle' | 'running' | 'completed' | 'failed' | 'terminated'

/** 执行步骤状态 */
export type StepStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped'

/** 子代理运行记录 */
export interface SubagentRun {
  /** 运行 ID */
  id: string
  /** 任务名称 */
  taskName: string
  /** 状态 */
  status: SubagentStatus
  /** 开始时间 */
  startedAt: string
  /** 结束时间 */
  finishedAt?: string
  /** 已运行时间（毫秒） */
  elapsedMs: number
  /** 当前步骤 */
  currentStep?: string
  /** 执行步骤列表 */
  steps: SubagentStep[]
  /** 模型名称 */
  model?: string
  /** 优先级 */
  priority: 'low' | 'normal' | 'high'
}

/** 子代理执行步骤 */
export interface SubagentStep {
  /** 步骤 ID */
  id: string
  /** 步骤名称 */
  name: string
  /** 状态 */
  status: StepStatus
  /** 开始时间 */
  startedAt?: string
  /** 结束时间 */
  finishedAt?: string
  /** 耗时（毫秒） */
  duration?: number
  /** 输出摘要 */
  output?: string
  /** 错误信息 */
  error?: string
}
