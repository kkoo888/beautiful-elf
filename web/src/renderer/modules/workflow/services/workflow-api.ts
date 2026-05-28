/** 工作流 API 服务（mock 实现） */

import { generateId } from '@/utils'
import type {
  Workflow,
  WorkflowRun,
  WorkflowTemplate,
  WorkflowFormInput,
  WorkflowNode,
  WorkflowEdge,
  NodeRun,
} from '../types/workflow'

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

// ─── Mock 数据 ────────────────────────────────────────────

const now = Date.now()

function makeNodes(overrides: Partial<WorkflowNode>[]): WorkflowNode[] {
  return overrides.map((o) => ({
    id: o.id ?? generateId(),
    type: o.type ?? 'task',
    label: o.label ?? '',
    position: o.position ?? { x: 0, y: 0 },
    config: o.config ?? {},
    status: o.status ?? 'idle',
  }))
}

const mockNodes1 = makeNodes([
  { id: 'n1', type: 'start', label: '开始', position: { x: 250, y: 0 } },
  { id: 'n2', type: 'task', label: '接收输入', position: { x: 250, y: 100 } },
  { id: 'n3', type: 'task', label: '意图识别', position: { x: 250, y: 200 } },
  { id: 'n4', type: 'condition', label: '路由分发', position: { x: 250, y: 300 } },
  { id: 'n5', type: 'task', label: '执行任务', position: { x: 150, y: 400 } },
  { id: 'n6', type: 'task', label: '输出结果', position: { x: 250, y: 500 } },
  { id: 'n7', type: 'end', label: '结束', position: { x: 250, y: 600 } },
])

const mockEdges1: WorkflowEdge[] = [
  { id: 'e1', source: 'n1', target: 'n2' },
  { id: 'e2', source: 'n2', target: 'n3' },
  { id: 'e3', source: 'n3', target: 'n4' },
  { id: 'e4', source: 'n4', target: 'n5' },
  { id: 'e5', source: 'n5', target: 'n6' },
  { id: 'e6', source: 'n6', target: 'n7' },
]

const mockNodes2 = makeNodes([
  { id: 'n1', type: 'start', label: '开始', position: { x: 250, y: 0 } },
  { id: 'n2', type: 'task', label: '数据采集', position: { x: 250, y: 100 } },
  { id: 'n3', type: 'task', label: '数据清洗', position: { x: 250, y: 200 } },
  { id: 'n4', type: 'parallel', label: '分析处理', position: { x: 250, y: 300 } },
  { id: 'n5', type: 'task', label: '生成报告', position: { x: 250, y: 400 } },
  { id: 'n6', type: 'end', label: '结束', position: { x: 250, y: 500 } },
])

const mockEdges2: WorkflowEdge[] = [
  { id: 'e1', source: 'n1', target: 'n2' },
  { id: 'e2', source: 'n2', target: 'n3' },
  { id: 'e3', source: 'n3', target: 'n4' },
  { id: 'e4', source: 'n4', target: 'n5' },
  { id: 'e5', source: 'n5', target: 'n6' },
]

const mockWorkflows: Workflow[] = [
  {
    id: 'wf-001',
    name: 'AI 对话处理流程',
    description: '接收用户输入，进行意图识别和路由分发',
    status: 'completed',
    triggerType: 'event',
    nodes: mockNodes1,
    edges: mockEdges1,
    createdAt: now - 30 * 86400_000,
    updatedAt: now - 2 * 86400_000,
    lastRunAt: now - 3600_000,
    lastRunStatus: 'success',
    runCount: 156,
  },
  {
    id: 'wf-002',
    name: '数据分析流水线',
    description: '自动采集、清洗、分析数据并生成报告',
    status: 'completed',
    triggerType: 'schedule',
    nodes: mockNodes2,
    edges: mockEdges2,
    createdAt: now - 14 * 86400_000,
    updatedAt: now - 86400_000,
    lastRunAt: now - 7200_000,
    lastRunStatus: 'success',
    runCount: 42,
  },
  {
    id: 'wf-003',
    name: '知识库同步',
    description: '定期同步外部知识库内容',
    status: 'failed',
    triggerType: 'schedule',
    nodes: makeNodes([
      { id: 'n1', type: 'start', label: '开始', position: { x: 250, y: 0 } },
      { id: 'n2', type: 'task', label: '检查更新', position: { x: 250, y: 100 } },
      { id: 'n3', type: 'task', label: '下载内容', position: { x: 250, y: 200 } },
      { id: 'n4', type: 'task', label: '索引构建', position: { x: 250, y: 300 } },
      { id: 'n5', type: 'end', label: '结束', position: { x: 250, y: 400 } },
    ]),
    edges: [
      { id: 'e1', source: 'n1', target: 'n2' },
      { id: 'e2', source: 'n2', target: 'n3' },
      { id: 'e3', source: 'n3', target: 'n4' },
      { id: 'e4', source: 'n4', target: 'n5' },
    ],
    createdAt: now - 60 * 86400_000,
    updatedAt: now - 10 * 86400_000,
    lastRunAt: now - 10 * 86400_000,
    lastRunStatus: 'failed',
    runCount: 89,
  },
  {
    id: 'wf-004',
    name: '日程提醒推送',
    description: '根据日程设置自动推送提醒通知',
    status: 'running',
    triggerType: 'schedule',
    nodes: makeNodes([
      { id: 'n1', type: 'start', label: '开始', position: { x: 250, y: 0 } },
      { id: 'n2', type: 'task', label: '扫描日程', position: { x: 250, y: 100 } },
      { id: 'n3', type: 'condition', label: '筛选待提醒', position: { x: 250, y: 200 } },
      { id: 'n4', type: 'task', label: '发送通知', position: { x: 250, y: 300 } },
      { id: 'n5', type: 'end', label: '结束', position: { x: 250, y: 400 } },
    ]),
    edges: [
      { id: 'e1', source: 'n1', target: 'n2' },
      { id: 'e2', source: 'n2', target: 'n3' },
      { id: 'e3', source: 'n3', target: 'n4' },
      { id: 'e4', source: 'n4', target: 'n5' },
    ],
    createdAt: now - 45 * 86400_000,
    updatedAt: now,
    lastRunAt: now - 1800_000,
    lastRunStatus: 'success',
    runCount: 312,
  },
  {
    id: 'wf-005',
    name: '草稿工作流',
    description: '尚未完成编排的工作流',
    status: 'draft',
    triggerType: 'manual',
    nodes: makeNodes([
      { id: 'n1', type: 'start', label: '开始', position: { x: 250, y: 0 } },
      { id: 'n2', type: 'task', label: '步骤 1', position: { x: 250, y: 100 } },
      { id: 'n3', type: 'end', label: '结束', position: { x: 250, y: 200 } },
    ]),
    edges: [
      { id: 'e1', source: 'n1', target: 'n2' },
      { id: 'e2', source: 'n2', target: 'n3' },
    ],
    createdAt: now - 86400_000,
    updatedAt: now - 86400_000,
    runCount: 0,
  },
]

const mockRuns: WorkflowRun[] = [
  {
    id: 'run-001',
    workflowId: 'wf-001',
    workflowName: 'AI 对话处理流程',
    status: 'success',
    startedAt: now - 3600_000,
    finishedAt: now - 3540_000,
    duration: 60000,
    nodeRuns: [
      {
        nodeId: 'n1',
        nodeName: '开始',
        status: 'success',
        startedAt: now - 3600_000,
        finishedAt: now - 3595_000,
        duration: 5000,
      },
      {
        nodeId: 'n2',
        nodeName: '接收输入',
        status: 'success',
        startedAt: now - 3595_000,
        finishedAt: now - 3585_000,
        duration: 10000,
      },
      {
        nodeId: 'n3',
        nodeName: '意图识别',
        status: 'success',
        startedAt: now - 3585_000,
        finishedAt: now - 3565_000,
        duration: 20000,
      },
      {
        nodeId: 'n4',
        nodeName: '路由分发',
        status: 'success',
        startedAt: now - 3565_000,
        finishedAt: now - 3555_000,
        duration: 10000,
      },
      {
        nodeId: 'n5',
        nodeName: '执行任务',
        status: 'success',
        startedAt: now - 3555_000,
        finishedAt: now - 3545_000,
        duration: 10000,
      },
      {
        nodeId: 'n6',
        nodeName: '输出结果',
        status: 'success',
        startedAt: now - 3545_000,
        finishedAt: now - 3540_000,
        duration: 5000,
      },
    ],
  },
  {
    id: 'run-002',
    workflowId: 'wf-002',
    workflowName: '数据分析流水线',
    status: 'running',
    startedAt: now - 1200_000,
    nodeRuns: [
      {
        nodeId: 'n1',
        nodeName: '开始',
        status: 'success',
        startedAt: now - 1200_000,
        finishedAt: now - 1195_000,
        duration: 5000,
      },
      {
        nodeId: 'n2',
        nodeName: '数据采集',
        status: 'success',
        startedAt: now - 1195_000,
        finishedAt: now - 900_000,
        duration: 295000,
      },
      {
        nodeId: 'n3',
        nodeName: '数据清洗',
        status: 'success',
        startedAt: now - 900_000,
        finishedAt: now - 600_000,
        duration: 300000,
      },
      { nodeId: 'n4', nodeName: '分析处理', status: 'running', startedAt: now - 600_000 },
      { nodeId: 'n5', nodeName: '生成报告', status: 'idle' },
    ],
  },
  {
    id: 'run-003',
    workflowId: 'wf-003',
    workflowName: '知识库同步',
    status: 'failed',
    startedAt: now - 10 * 86400_000,
    finishedAt: now - 10 * 86400_000 + 45000,
    duration: 45000,
    nodeRuns: [
      {
        nodeId: 'n1',
        nodeName: '开始',
        status: 'success',
        startedAt: now - 10 * 86400_000,
        finishedAt: now - 10 * 86400_000 + 5000,
        duration: 5000,
      },
      {
        nodeId: 'n2',
        nodeName: '检查更新',
        status: 'success',
        startedAt: now - 10 * 86400_000 + 5000,
        finishedAt: now - 10 * 86400_000 + 10000,
        duration: 5000,
      },
      {
        nodeId: 'n3',
        nodeName: '下载内容',
        status: 'failed',
        startedAt: now - 10 * 86400_000 + 10000,
        finishedAt: now - 10 * 86400_000 + 45000,
        duration: 35000,
        error: '连接超时：无法访问远程知识库',
      },
      { nodeId: 'n4', nodeName: '索引构建', status: 'skipped' },
    ],
  },
]

const mockTemplates: WorkflowTemplate[] = [
  {
    id: 'tpl-001',
    name: '数据处理流水线',
    description: '采集 → 清洗 → 分析 → 报告的标准数据处理流程',
    icon: '📊',
    category: '数据',
    nodes: makeNodes([
      { id: 't1', type: 'start', label: '开始', position: { x: 250, y: 0 } },
      { id: 't2', type: 'task', label: '数据采集', position: { x: 250, y: 100 } },
      { id: 't3', type: 'task', label: '数据清洗', position: { x: 250, y: 200 } },
      { id: 't4', type: 'parallel', label: '分析处理', position: { x: 250, y: 300 } },
      { id: 't5', type: 'task', label: '生成报告', position: { x: 250, y: 400 } },
      { id: 't6', type: 'end', label: '结束', position: { x: 250, y: 500 } },
    ]),
    edges: [
      { id: 'te1', source: 't1', target: 't2' },
      { id: 'te2', source: 't2', target: 't3' },
      { id: 'te3', source: 't3', target: 't4' },
      { id: 'te4', source: 't4', target: 't5' },
      { id: 'te5', source: 't5', target: 't6' },
    ],
  },
  {
    id: 'tpl-002',
    name: '定时任务链',
    description: '按计划执行周期性任务，支持多步骤串联',
    icon: '⏰',
    category: '自动化',
    nodes: makeNodes([
      { id: 't1', type: 'start', label: '触发', position: { x: 250, y: 0 } },
      { id: 't2', type: 'condition', label: '检查条件', position: { x: 250, y: 100 } },
      { id: 't3', type: 'task', label: '执行任务', position: { x: 250, y: 220 } },
      { id: 't4', type: 'task', label: '发送通知', position: { x: 250, y: 320 } },
      { id: 't5', type: 'end', label: '完成', position: { x: 250, y: 420 } },
    ]),
    edges: [
      { id: 'te1', source: 't1', target: 't2' },
      { id: 'te2', source: 't2', target: 't3' },
      { id: 'te3', source: 't3', target: 't4' },
      { id: 'te4', source: 't4', target: 't5' },
    ],
  },
  {
    id: 'tpl-003',
    name: '条件分支',
    description: '支持条件判断和多路径分支的工作流模板',
    icon: '🔀',
    category: '逻辑',
    nodes: makeNodes([
      { id: 't1', type: 'start', label: '开始', position: { x: 250, y: 0 } },
      { id: 't2', type: 'condition', label: '条件判断', position: { x: 250, y: 120 } },
      { id: 't3', type: 'task', label: '分支 A', position: { x: 100, y: 250 } },
      { id: 't4', type: 'task', label: '分支 B', position: { x: 400, y: 250 } },
      { id: 't5', type: 'task', label: '汇合处理', position: { x: 250, y: 370 } },
      { id: 't6', type: 'end', label: '结束', position: { x: 250, y: 470 } },
    ]),
    edges: [
      { id: 'te1', source: 't1', target: 't2' },
      { id: 'te2', source: 't2', target: 't3', label: '是' },
      { id: 'te3', source: 't2', target: 't4', label: '否' },
      { id: 'te4', source: 't3', target: 't5' },
      { id: 'te5', source: 't4', target: 't5' },
      { id: 'te6', source: 't5', target: 't6' },
    ],
  },
]

let workflowStore = [...mockWorkflows]
let runStore = [...mockRuns]

// ─── API 函数 ─────────────────────────────────────────────

export async function fetchWorkflows(): Promise<Workflow[]> {
  await delay()
  return [...workflowStore]
}

export async function fetchWorkflowById(id: string): Promise<Workflow | undefined> {
  await delay()
  return workflowStore.find((w) => w.id === id)
}

export async function createWorkflow(input: WorkflowFormInput): Promise<Workflow> {
  await delay()
  const workflow: Workflow = {
    id: generateId(),
    name: input.name,
    description: input.description ?? '',
    status: 'draft',
    triggerType: input.triggerType,
    nodes: input.nodes,
    edges: input.edges,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    runCount: 0,
  }
  workflowStore.push(workflow)
  return workflow
}

export async function updateWorkflow(
  id: string,
  input: Partial<WorkflowFormInput>
): Promise<Workflow> {
  await delay()
  const idx = workflowStore.findIndex((w) => w.id === id)
  if (idx === -1) throw new Error('Workflow not found')
  workflowStore[idx] = { ...workflowStore[idx], ...input, updatedAt: Date.now() }
  return workflowStore[idx]
}

export async function deleteWorkflow(id: string): Promise<void> {
  await delay()
  workflowStore = workflowStore.filter((w) => w.id !== id)
}

export async function fetchWorkflowRuns(workflowId?: string): Promise<WorkflowRun[]> {
  await delay()
  if (workflowId) return runStore.filter((r) => r.workflowId === workflowId)
  return [...runStore]
}

export async function fetchWorkflowTemplates(): Promise<WorkflowTemplate[]> {
  await delay()
  return [...mockTemplates]
}

export async function createFromTemplate(templateId: string): Promise<Workflow> {
  await delay()
  const tpl = mockTemplates.find((t) => t.id === templateId)
  if (!tpl) throw new Error('Template not found')
  const nodes = tpl.nodes.map((n) => ({ ...n, id: `node-${Date.now()}-${n.id}` }))
  const edges = tpl.edges.map((e) => ({ ...e, id: `e-${Date.now()}-${e.id}` }))
  return createWorkflow({
    name: `${tpl.name}（副本）`,
    description: tpl.description,
    triggerType: 'manual',
    nodes,
    edges,
  })
}

/** 保存 DAG（节点 + 边） */
export async function saveWorkflowDag(
  workflowId: string,
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): Promise<Workflow> {
  await delay()
  const wf = workflowStore.find((w) => w.id === workflowId)
  if (!wf) throw new Error('Workflow not found')
  wf.nodes = nodes
  wf.edges = edges
  wf.updatedAt = Date.now()
  return wf
}

/** 运行工作流 */
export async function runWorkflow(id: string): Promise<void> {
  await delay()
  const wf = workflowStore.find((w) => w.id === id)
  if (!wf) throw new Error('Workflow not found')
  wf.status = 'running'
  wf.lastRunAt = Date.now()

  // 创建运行记录
  const run: WorkflowRun = {
    id: generateId(),
    workflowId: id,
    workflowName: wf.name,
    status: 'running',
    startedAt: Date.now(),
    nodeRuns: wf.nodes
      .filter((n) => n.type !== 'start' && n.type !== 'end')
      .map((n) => ({
        nodeId: n.id,
        nodeName: n.label,
        status: 'idle' as const,
      })),
  }
  runStore.unshift(run)
}

/** 停止工作流 */
export async function stopWorkflow(id: string): Promise<void> {
  await delay()
  const wf = workflowStore.find((w) => w.id === id)
  if (!wf) throw new Error('Workflow not found')
  wf.status = 'draft'

  // 更新运行记录
  const runningRun = runStore.find((r) => r.workflowId === id && r.status === 'running')
  if (runningRun) {
    runningRun.status = 'cancelled'
    runningRun.finishedAt = Date.now()
    runningRun.duration = runningRun.finishedAt - runningRun.startedAt
  }
}

/** 复制工作流 */
export async function duplicateWorkflow(id: string): Promise<Workflow> {
  await delay()
  const wf = workflowStore.find((w) => w.id === id)
  if (!wf) throw new Error('Workflow not found')
  const newNodes = wf.nodes.map((n) => ({
    ...n,
    id: `node-${Date.now()}-${n.id}`,
    status: 'idle' as const,
  }))
  const newEdges = wf.edges.map((e) => ({ ...e, id: `e-${Date.now()}-${e.id}` }))
  return createWorkflow({
    name: `${wf.name}（副本）`,
    description: wf.description,
    triggerType: wf.triggerType,
    nodes: newNodes,
    edges: newEdges,
  })
}
