/** 子代理 API 服务（mock 实现） */

import { generateId } from '@/utils'
import type { SubagentRun, SubagentStep } from '../types/subagent'

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

// ─── Mock 数据 ────────────────────────────────────────────

const now = new Date()

function iso(d: Date): string {
  return d.toISOString()
}

const mockSteps1: SubagentStep[] = [
  {
    id: generateId(),
    name: '解析用户需求',
    status: 'success',
    startedAt: iso(new Date(now.getTime() - 1800_000)),
    finishedAt: iso(new Date(now.getTime() - 1740_000)),
    duration: 60000,
    output: '识别到 3 个子任务',
  },
  {
    id: generateId(),
    name: '生成代码框架',
    status: 'success',
    startedAt: iso(new Date(now.getTime() - 1740_000)),
    finishedAt: iso(new Date(now.getTime() - 1500_000)),
    duration: 240000,
    output: '生成了 5 个文件',
  },
  {
    id: generateId(),
    name: '编写单元测试',
    status: 'running',
    startedAt: iso(new Date(now.getTime() - 1500_000)),
  },
  { id: generateId(), name: '代码审查', status: 'pending' },
  { id: generateId(), name: '提交代码', status: 'pending' },
]

const mockSteps2: SubagentStep[] = [
  {
    id: generateId(),
    name: '分析错误日志',
    status: 'success',
    startedAt: iso(new Date(now.getTime() - 600_000)),
    finishedAt: iso(new Date(now.getTime() - 540_000)),
    duration: 60000,
    output: '定位到 2 个异常点',
  },
  {
    id: generateId(),
    name: '复现问题',
    status: 'success',
    startedAt: iso(new Date(now.getTime() - 540_000)),
    finishedAt: iso(new Date(now.getTime() - 420_000)),
    duration: 120000,
    output: '成功复现',
  },
  {
    id: generateId(),
    name: '修复代码',
    status: 'success',
    startedAt: iso(new Date(now.getTime() - 420_000)),
    finishedAt: iso(new Date(now.getTime() - 300_000)),
    duration: 120000,
    output: '修改了 3 个文件',
  },
  {
    id: generateId(),
    name: '回归测试',
    status: 'running',
    startedAt: iso(new Date(now.getTime() - 300_000)),
  },
]

const mockSteps3: SubagentStep[] = [
  {
    id: generateId(),
    name: '搜索文献资料',
    status: 'success',
    startedAt: iso(new Date(now.getTime() - 300_000)),
    finishedAt: iso(new Date(now.getTime() - 240_000)),
    duration: 60000,
    output: '找到 12 篇相关文献',
  },
  {
    id: generateId(),
    name: '提取关键信息',
    status: 'success',
    startedAt: iso(new Date(now.getTime() - 240_000)),
    finishedAt: iso(new Date(now.getTime() - 180_000)),
    duration: 60000,
    output: '提取了 28 条关键数据',
  },
  {
    id: generateId(),
    name: '生成摘要报告',
    status: 'success',
    startedAt: iso(new Date(now.getTime() - 180_000)),
    finishedAt: iso(new Date(now.getTime() - 120_000)),
    duration: 60000,
    output: '报告已生成',
  },
]

const mockRuns: SubagentRun[] = [
  {
    id: 'sa-001',
    taskName: '编写认证模块单元测试',
    status: 'running',
    startedAt: iso(new Date(now.getTime() - 1800_000)),
    elapsedMs: 1800_000,
    currentStep: '编写单元测试',
    steps: mockSteps1,
    model: 'claude-sonnet-4',
    priority: 'high',
  },
  {
    id: 'sa-002',
    taskName: '修复登录超时 Bug',
    status: 'running',
    startedAt: iso(new Date(now.getTime() - 600_000)),
    elapsedMs: 600_000,
    currentStep: '回归测试',
    steps: mockSteps2,
    model: 'claude-sonnet-4',
    priority: 'high',
  },
  {
    id: 'sa-003',
    taskName: '调研 RAG 技术方案',
    status: 'completed',
    startedAt: iso(new Date(now.getTime() - 3600_000)),
    finishedAt: iso(new Date(now.getTime() - 3420_000)),
    elapsedMs: 180_000,
    steps: mockSteps3,
    model: 'gpt-4o',
    priority: 'normal',
  },
  {
    id: 'sa-004',
    taskName: '优化数据库查询性能',
    status: 'failed',
    startedAt: iso(new Date(now.getTime() - 7200_000)),
    finishedAt: iso(new Date(now.getTime() - 6900_000)),
    elapsedMs: 300_000,
    steps: [
      { id: generateId(), name: '分析慢查询', status: 'success', duration: 120000 },
      { id: generateId(), name: '优化索引', status: 'failed', error: '无法连接数据库' },
    ],
    model: 'claude-sonnet-4',
    priority: 'normal',
  },
]

let runStore = [...mockRuns]

// ─── API 函数 ─────────────────────────────────────────────

/** 获取子代理运行列表 */
export async function fetchSubagentRuns(): Promise<SubagentRun[]> {
  await delay()
  return [...runStore]
}

/** 获取运行详情 */
export async function fetchSubagentRunById(id: string): Promise<SubagentRun | undefined> {
  await delay()
  return runStore.find((r) => r.id === id)
}

/** 终止子代理运行 */
export async function stopSubagentRun(id: string): Promise<SubagentRun> {
  await delay()
  const run = runStore.find((r) => r.id === id)
  if (!run) throw new Error('Run not found')
  run.status = 'terminated'
  run.finishedAt = new Date().toISOString()
  return run
}

/** 终止全部运行中的子代理 */
export async function stopAllSubagentRuns(): Promise<number> {
  await delay()
  let count = 0
  for (const run of runStore) {
    if (run.status === 'running') {
      run.status = 'terminated'
      run.finishedAt = new Date().toISOString()
      count++
    }
  }
  return count
}
