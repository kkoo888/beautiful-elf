/** 工作流模块类型定义 */

// ─── DAG 节点 & 边 ─────────────────────────────────────────

/** DAG 节点类型 */
export type DagNodeType = 'start' | 'end' | 'task' | 'condition' | 'parallel'

/** 节点执行状态 */
export type NodeStatus = 'idle' | 'running' | 'success' | 'failed' | 'skipped'

/** DAG 节点 */
export interface WorkflowNode {
  id: string
  type: DagNodeType
  label: string
  position: { x: number; y: number }
  config: Record<string, unknown>
  status: NodeStatus
}

/** DAG 边 */
export interface WorkflowEdge {
  id: string
  source: string
  target: string
  label?: string
  condition?: string
}

// ─── 工作流 ────────────────────────────────────────────────

/** 工作流状态 */
export type WorkflowStatus = 'draft' | 'running' | 'completed' | 'failed'

/** 触发方式 */
export type TriggerType = 'manual' | 'schedule' | 'event' | 'webhook'

/** 工作流定义（DAG 版） */
export interface Workflow {
  id: string
  name: string
  description: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  status: WorkflowStatus
  triggerType: TriggerType
  createdAt: number
  updatedAt: number
  lastRunAt?: number
  lastRunStatus?: NodeStatus
  runCount: number
}

// ─── 模板 ──────────────────────────────────────────────────

/** 工作流模板 */
export interface WorkflowTemplate {
  id: string
  name: string
  description: string
  icon: string
  category: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

// ─── 运行记录 ──────────────────────────────────────────────

/** 工作流运行记录 */
export interface WorkflowRun {
  id: string
  workflowId: string
  workflowName: string
  status: 'running' | 'success' | 'failed' | 'cancelled'
  startedAt: number
  finishedAt?: number
  duration?: number
  nodeRuns: NodeRun[]
}

/** 节点运行记录 */
export interface NodeRun {
  nodeId: string
  nodeName: string
  status: NodeStatus
  startedAt?: number
  finishedAt?: number
  duration?: number
  error?: string
}

// ─── 表单 ──────────────────────────────────────────────────

/** 工作流表单输入 */
export interface WorkflowFormInput {
  name: string
  description?: string
  triggerType: TriggerType
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}
