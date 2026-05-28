/** 工作流模块类型定义 */

/** 工作流状态 */
export type WorkflowStatus = 'draft' | 'active' | 'paused' | 'archived'

/** 触发方式 */
export type TriggerType = 'manual' | 'schedule' | 'event' | 'webhook'

/** 节点执行状态 */
export type NodeStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped'

/** 工作流步骤 */
export interface WorkflowStep {
  /** 步骤 ID */
  id: string
  /** 步骤名称 */
  name: string
  /** 步骤类型 */
  type: 'action' | 'condition' | 'loop' | 'parallel'
  /** 步骤描述 */
  description?: string
  /** 配置参数 */
  config: Record<string, unknown>
  /** 依赖的步骤 ID 列表 */
  dependsOn: string[]
  /** 排序序号 */
  order: number
}

/** 工作流定义 */
export interface Workflow {
  /** 工作流 ID */
  id: string
  /** 工作流名称 */
  name: string
  /** 描述 */
  description?: string
  /** 状态 */
  status: WorkflowStatus
  /** 触发方式 */
  triggerType: TriggerType
  /** 步骤列表 */
  steps: WorkflowStep[]
  /** 创建时间 */
  createdAt: string
  /** 更新时间 */
  updatedAt: string
  /** 最近运行时间 */
  lastRunAt?: string
  /** 最近运行状态 */
  lastRunStatus?: NodeStatus
  /** 运行次数 */
  runCount: number
}

/** 工作流运行记录 */
export interface WorkflowRun {
  /** 运行 ID */
  id: string
  /** 工作流 ID */
  workflowId: string
  /** 工作流名称 */
  workflowName: string
  /** 运行状态 */
  status: 'running' | 'success' | 'failed' | 'cancelled'
  /** 开始时间 */
  startedAt: string
  /** 结束时间 */
  finishedAt?: string
  /** 耗时（毫秒） */
  duration?: number
  /** 各节点运行状态 */
  nodeRuns: NodeRun[]
}

/** 节点运行记录 */
export interface NodeRun {
  /** 节点 ID */
  nodeId: string
  /** 节点名称 */
  nodeName: string
  /** 状态 */
  status: NodeStatus
  /** 开始时间 */
  startedAt?: string
  /** 结束时间 */
  finishedAt?: string
  /** 耗时（毫秒） */
  duration?: number
  /** 错误信息 */
  error?: string
}

/** 工作流模板 */
export interface WorkflowTemplate {
  /** 模板 ID */
  id: string
  /** 模板名称 */
  name: string
  /** 描述 */
  description: string
  /** 图标 */
  icon: string
  /** 分类 */
  category: string
  /** 预置步骤 */
  steps: Omit<WorkflowStep, 'id'>[]
}

/** 工作流表单输入 */
export interface WorkflowFormInput {
  name: string
  description?: string
  triggerType: TriggerType
  steps: WorkflowStep[]
}
