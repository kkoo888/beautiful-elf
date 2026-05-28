/** 工作流 API 服务（mock 实现） */

import { generateId } from '@/utils'
import type {
  Workflow,
  WorkflowRun,
  WorkflowTemplate,
  WorkflowFormInput,
  WorkflowStep,
  NodeRun,
} from '../types/workflow'

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

// ─── Mock 数据 ────────────────────────────────────────────

const now = new Date()

function iso(d: Date): string {
  return d.toISOString()
}

const mockSteps1: WorkflowStep[] = [
  { id: generateId(), name: '接收输入', type: 'action', config: {}, dependsOn: [], order: 0 },
  { id: generateId(), name: '意图识别', type: 'action', config: {}, dependsOn: [], order: 1 },
  { id: generateId(), name: '路由分发', type: 'condition', config: {}, dependsOn: [], order: 2 },
  { id: generateId(), name: '执行任务', type: 'action', config: {}, dependsOn: [], order: 3 },
  { id: generateId(), name: '输出结果', type: 'action', config: {}, dependsOn: [], order: 4 },
]

const mockSteps2: WorkflowStep[] = [
  { id: generateId(), name: '数据采集', type: 'action', config: {}, dependsOn: [], order: 0 },
  { id: generateId(), name: '数据清洗', type: 'action', config: {}, dependsOn: [], order: 1 },
  { id: generateId(), name: '分析处理', type: 'parallel', config: {}, dependsOn: [], order: 2 },
  { id: generateId(), name: '生成报告', type: 'action', config: {}, dependsOn: [], order: 3 },
]

const mockWorkflows: Workflow[] = [
  {
    id: 'wf-001',
    name: 'AI 对话处理流程',
    description: '接收用户输入，进行意图识别和路由分发',
    status: 'active',
    triggerType: 'event',
    steps: mockSteps1,
    createdAt: iso(new Date(now.getTime() - 30 * 86400_000)),
    updatedAt: iso(new Date(now.getTime() - 2 * 86400_000)),
    lastRunAt: iso(new Date(now.getTime() - 3600_000)),
    lastRunStatus: 'success',
    runCount: 156,
  },
  {
    id: 'wf-002',
    name: '数据分析流水线',
    description: '自动采集、清洗、分析数据并生成报告',
    status: 'active',
    triggerType: 'schedule',
    steps: mockSteps2,
    createdAt: iso(new Date(now.getTime() - 14 * 86400_000)),
    updatedAt: iso(new Date(now.getTime() - 86400_000)),
    lastRunAt: iso(new Date(now.getTime() - 7200_000)),
    lastRunStatus: 'success',
    runCount: 42,
  },
  {
    id: 'wf-003',
    name: '知识库同步',
    description: '定期同步外部知识库内容',
    status: 'paused',
    triggerType: 'schedule',
    steps: [
      { id: generateId(), name: '检查更新', type: 'action', config: {}, dependsOn: [], order: 0 },
      { id: generateId(), name: '下载内容', type: 'action', config: {}, dependsOn: [], order: 1 },
      { id: generateId(), name: '索引构建', type: 'action', config: {}, dependsOn: [], order: 2 },
    ],
    createdAt: iso(new Date(now.getTime() - 60 * 86400_000)),
    updatedAt: iso(new Date(now.getTime() - 10 * 86400_000)),
    lastRunAt: iso(new Date(now.getTime() - 10 * 86400_000)),
    lastRunStatus: 'failed',
    runCount: 89,
  },
  {
    id: 'wf-004',
    name: '日程提醒推送',
    description: '根据日程设置自动推送提醒通知',
    status: 'active',
    triggerType: 'schedule',
    steps: [
      { id: generateId(), name: '扫描日程', type: 'action', config: {}, dependsOn: [], order: 0 },
      { id: generateId(), name: '筛选待提醒', type: 'condition', config: {}, dependsOn: [], order: 1 },
      { id: generateId(), name: '发送通知', type: 'action', config: {}, dependsOn: [], order: 2 },
    ],
    createdAt: iso(new Date(now.getTime() - 45 * 86400_000)),
    updatedAt: iso(now),
    lastRunAt: iso(new Date(now.getTime() - 1800_000)),
    lastRunStatus: 'success',
    runCount: 312,
  },
  {
    id: 'wf-005',
    name: '草稿工作流',
    description: '尚未完成编排的工作流',
    status: 'draft',
    triggerType: 'manual',
    steps: [
      { id: generateId(), name: '步骤 1', type: 'action', config: {}, dependsOn: [], order: 0 },
    ],
    createdAt: iso(new Date(now.getTime() - 86400_000)),
    updatedAt: iso(new Date(now.getTime() - 86400_000)),
    runCount: 0,
  },
]

const mockRuns: WorkflowRun[] = [
  {
    id: 'run-001',
    workflowId: 'wf-001',
    workflowName: 'AI 对话处理流程',
    status: 'success',
    startedAt: iso(new Date(now.getTime() - 3600_000)),
    finishedAt: iso(new Date(now.getTime() - 3540_000)),
    duration: 60000,
    nodeRuns: [
      { nodeId: 'n1', nodeName: '接收输入', status: 'success', startedAt: iso(new Date(now.getTime() - 3600_000)), finishedAt: iso(new Date(now.getTime() - 3590_000)), duration: 10000 },
      { nodeId: 'n2', nodeName: '意图识别', status: 'success', startedAt: iso(new Date(now.getTime() - 3590_000)), finishedAt: iso(new Date(now.getTime() - 3570_000)), duration: 20000 },
      { nodeId: 'n3', nodeName: '路由分发', status: 'success', startedAt: iso(new Date(now.getTime() - 3570_000)), finishedAt: iso(new Date(now.getTime() - 3560_000)), duration: 10000 },
      { nodeId: 'n4', nodeName: '执行任务', status: 'success', startedAt: iso(new Date(now.getTime() - 3560_000)), finishedAt: iso(new Date(now.getTime() - 3545_000)), duration: 15000 },
      { nodeId: 'n5', nodeName: '输出结果', status: 'success', startedAt: iso(new Date(now.getTime() - 3545_000)), finishedAt: iso(new Date(now.getTime() - 3540_000)), duration: 5000 },
    ],
  },
  {
    id: 'run-002',
    workflowId: 'wf-002',
    workflowName: '数据分析流水线',
    status: 'running',
    startedAt: iso(new Date(now.getTime() - 1200_000)),
    nodeRuns: [
      { nodeId: 'n1', nodeName: '数据采集', status: 'success', startedAt: iso(new Date(now.getTime() - 1200_000)), finishedAt: iso(new Date(now.getTime() - 900_000)), duration: 300000 },
      { nodeId: 'n2', nodeName: '数据清洗', status: 'success', startedAt: iso(new Date(now.getTime() - 900_000)), finishedAt: iso(new Date(now.getTime() - 600_000)), duration: 300000 },
      { nodeId: 'n3', nodeName: '分析处理', status: 'running', startedAt: iso(new Date(now.getTime() - 600_000)) },
      { nodeId: 'n4', nodeName: '生成报告', status: 'pending' },
    ],
  },
  {
    id: 'run-003',
    workflowId: 'wf-003',
    workflowName: '知识库同步',
    status: 'failed',
    startedAt: iso(new Date(now.getTime() - 10 * 86400_000)),
    finishedAt: iso(new Date(now.getTime() - 10 * 86400_000 + 45000)),
    duration: 45000,
    nodeRuns: [
      { nodeId: 'n1', nodeName: '检查更新', status: 'success', startedAt: iso(new Date(now.getTime() - 10 * 86400_000)), finishedAt: iso(new Date(now.getTime() - 10 * 86400_000 + 10000)), duration: 10000 },
      { nodeId: 'n2', nodeName: '下载内容', status: 'failed', startedAt: iso(new Date(now.getTime() - 10 * 86400_000 + 10000)), finishedAt: iso(new Date(now.getTime() - 10 * 86400_000 + 45000)), duration: 35000, error: '连接超时：无法访问远程知识库' },
      { nodeId: 'n3', nodeName: '索引构建', status: 'skipped' },
    ],
  },
]

const mockTemplates: WorkflowTemplate[] = [
  {
    id: 'tpl-001',
    name: '对话处理流程',
    description: '标准的 AI 对话处理管线，包含意图识别和路由分发',
    icon: '💬',
    category: 'AI',
    steps: [
      { name: '接收输入', type: 'action', config: {}, dependsOn: [], order: 0 },
      { name: '意图识别', type: 'action', config: {}, dependsOn: [], order: 1 },
      { name: '路由分发', type: 'condition', config: {}, dependsOn: [], order: 2 },
      { name: '生成回复', type: 'action', config: {}, dependsOn: [], order: 3 },
    ],
  },
  {
    id: 'tpl-002',
    name: '数据处理流水线',
    description: '采集 → 清洗 → 分析 → 报告的标准数据处理流程',
    icon: '📊',
    category: '数据',
    steps: [
      { name: '数据采集', type: 'action', config: {}, dependsOn: [], order: 0 },
      { name: '数据清洗', type: 'action', config: {}, dependsOn: [], order: 1 },
      { name: '分析处理', type: 'parallel', config: {}, dependsOn: [], order: 2 },
      { name: '生成报告', type: 'action', config: {}, dependsOn: [], order: 3 },
    ],
  },
  {
    id: 'tpl-003',
    name: '定时任务模板',
    description: '按计划执行周期性任务',
    icon: '⏰',
    category: '自动化',
    steps: [
      { name: '检查条件', type: 'condition', config: {}, dependsOn: [], order: 0 },
      { name: '执行任务', type: 'action', config: {}, dependsOn: [], order: 1 },
      { name: '发送通知', type: 'action', config: {}, dependsOn: [], order: 2 },
    ],
  },
  {
    id: 'tpl-004',
    name: '审批流程',
    description: '多级审批工作流，支持条件分支',
    icon: '✅',
    category: '协作',
    steps: [
      { name: '提交申请', type: 'action', config: {}, dependsOn: [], order: 0 },
      { name: '自动审核', type: 'condition', config: {}, dependsOn: [], order: 1 },
      { name: '人工审批', type: 'action', config: {}, dependsOn: [], order: 2 },
      { name: '结果通知', type: 'action', config: {}, dependsOn: [], order: 3 },
    ],
  },
]

let workflowStore = [...mockWorkflows]
let runStore = [...mockRuns]

// ─── API 函数 ─────────────────────────────────────────────

/** 获取工作流列表 */
export async function fetchWorkflows(): Promise<Workflow[]> {
  await delay()
  return [...workflowStore]
}

/** 获取工作流详情 */
export async function fetchWorkflowById(id: string): Promise<Workflow | undefined> {
  await delay()
  return workflowStore.find((w) => w.id === id)
}

/** 创建工作流 */
export async function createWorkflow(input: WorkflowFormInput): Promise<Workflow> {
  await delay()
  const workflow: Workflow = {
    id: generateId(),
    name: input.name,
    description: input.description,
    status: 'draft',
    triggerType: input.triggerType,
    steps: input.steps,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    runCount: 0,
  }
  workflowStore.push(workflow)
  return workflow
}

/** 更新工作流 */
export async function updateWorkflow(id: string, input: Partial<WorkflowFormInput>): Promise<Workflow> {
  await delay()
  const idx = workflowStore.findIndex((w) => w.id === id)
  if (idx === -1) throw new Error('Workflow not found')
  workflowStore[idx] = { ...workflowStore[idx], ...input, updatedAt: new Date().toISOString() }
  return workflowStore[idx]
}

/** 删除工作流 */
export async function deleteWorkflow(id: string): Promise<void> {
  await delay()
  workflowStore = workflowStore.filter((w) => w.id !== id)
}

/** 获取工作流运行记录 */
export async function fetchWorkflowRuns(workflowId?: string): Promise<WorkflowRun[]> {
  await delay()
  if (workflowId) return runStore.filter((r) => r.workflowId === workflowId)
  return [...runStore]
}

/** 获取工作流模板列表 */
export async function fetchWorkflowTemplates(): Promise<WorkflowTemplate[]> {
  await delay()
  return [...mockTemplates]
}

/** 从模板创建工作流 */
export async function createFromTemplate(templateId: string): Promise<Workflow> {
  await delay()
  const tpl = mockTemplates.find((t) => t.id === templateId)
  if (!tpl) throw new Error('Template not found')
  const steps: WorkflowStep[] = tpl.steps.map((s, i) => ({ ...s, id: generateId(), order: i }))
  return createWorkflow({ name: `${tpl.name}（副本）`, description: tpl.description, triggerType: 'manual', steps })
}

/** 重排工作流步骤 */
export async function reorderSteps(workflowId: string, stepIds: string[]): Promise<Workflow> {
  await delay()
  const wf = workflowStore.find((w) => w.id === workflowId)
  if (!wf) throw new Error('Workflow not found')
  const stepMap = new Map(wf.steps.map((s) => [s.id, s]))
  wf.steps = stepIds.map((id, order) => {
    const step = stepMap.get(id)
    if (!step) throw new Error(`Step ${id} not found`)
    return { ...step, order }
  })
  wf.updatedAt = new Date().toISOString()
  return wf
}
