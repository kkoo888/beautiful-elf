/** 工具管理 API 服务（mock 实现） */

import { generateId } from '@/utils'
import type { ToolInfo, ToolStats, ToolStatsSummary } from '../types/tools'

function delay(ms = 300): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

// ─── Mock 数据 ────────────────────────────────────────────

const now = new Date()

function iso(d: Date): string {
  return d.toISOString()
}

const mockTools: ToolInfo[] = [
  { id: 'tool-001', name: 'web_search', description: '网络搜索工具，支持实时信息检索', module: 'search', status: 'active', version: '1.2.0', registeredAt: iso(new Date(now.getTime() - 60 * 86400_000)), lastCalledAt: iso(new Date(now.getTime() - 1800_000)) },
  { id: 'tool-002', name: 'code_execute', description: '安全沙箱中执行代码片段', module: 'execution', status: 'active', version: '2.0.1', registeredAt: iso(new Date(now.getTime() - 45 * 86400_000)), lastCalledAt: iso(new Date(now.getTime() - 3600_000)) },
  { id: 'tool-003', name: 'file_read', description: '读取本地文件内容', module: 'filesystem', status: 'active', version: '1.0.0', registeredAt: iso(new Date(now.getTime() - 90 * 86400_000)), lastCalledAt: iso(new Date(now.getTime() - 600_000)) },
  { id: 'tool-004', name: 'file_write', description: '写入本地文件', module: 'filesystem', status: 'active', version: '1.0.0', registeredAt: iso(new Date(now.getTime() - 90 * 86400_000)), lastCalledAt: iso(new Date(now.getTime() - 1200_000)) },
  { id: 'tool-005', name: 'image_generate', description: 'AI 图片生成工具', module: 'media', status: 'active', version: '1.1.0', registeredAt: iso(new Date(now.getTime() - 30 * 86400_000)), lastCalledAt: iso(new Date(now.getTime() - 7200_000)) },
  { id: 'tool-006', name: 'translate', description: '多语言翻译工具', module: 'language', status: 'active', version: '1.3.0', registeredAt: iso(new Date(now.getTime() - 75 * 86400_000)), lastCalledAt: iso(new Date(now.getTime() - 900_000)) },
  { id: 'tool-007', name: 'calendar_api', description: '日历 API 集成', module: 'integration', status: 'active', version: '1.0.2', registeredAt: iso(new Date(now.getTime() - 50 * 86400_000)), lastCalledAt: iso(new Date(now.getTime() - 5400_000)) },
  { id: 'tool-008', name: 'email_send', description: '发送邮件通知', module: 'notification', status: 'inactive', version: '0.9.0', registeredAt: iso(new Date(now.getTime() - 20 * 86400_000)) },
  { id: 'tool-009', name: 'database_query', description: '数据库查询工具', module: 'data', status: 'active', version: '1.5.0', registeredAt: iso(new Date(now.getTime() - 80 * 86400_000)), lastCalledAt: iso(new Date(now.getTime() - 2400_000)) },
  { id: 'tool-010', name: 'api_call', description: '通用 HTTP API 调用工具', module: 'integration', status: 'error', version: '1.2.0', registeredAt: iso(new Date(now.getTime() - 40 * 86400_000)), lastCalledAt: iso(new Date(now.getTime() - 43200_000)) },
]

const mockStats: ToolStats[] = [
  { toolId: 'tool-001', toolName: 'web_search', callCount: 1247, successCount: 1198, failureCount: 49, successRate: 96.1, avgDurationMs: 1250, last24hCalls: 34 },
  { toolId: 'tool-002', toolName: 'code_execute', callCount: 856, successCount: 812, failureCount: 44, successRate: 94.9, avgDurationMs: 3420, last24hCalls: 18 },
  { toolId: 'tool-003', toolName: 'file_read', callCount: 2341, successCount: 2338, failureCount: 3, successRate: 99.9, avgDurationMs: 45, last24hCalls: 89 },
  { toolId: 'tool-004', toolName: 'file_write', callCount: 1892, successCount: 1887, failureCount: 5, successRate: 99.7, avgDurationMs: 62, last24hCalls: 67 },
  { toolId: 'tool-005', toolName: 'image_generate', callCount: 234, successCount: 221, failureCount: 13, successRate: 94.4, avgDurationMs: 8500, last24hCalls: 5 },
  { toolId: 'tool-006', toolName: 'translate', callCount: 1567, successCount: 1560, failureCount: 7, successRate: 99.6, avgDurationMs: 320, last24hCalls: 42 },
  { toolId: 'tool-007', toolName: 'calendar_api', callCount: 445, successCount: 430, failureCount: 15, successRate: 96.6, avgDurationMs: 580, last24hCalls: 12 },
  { toolId: 'tool-008', toolName: 'email_send', callCount: 89, successCount: 78, failureCount: 11, successRate: 87.6, avgDurationMs: 1100, last24hCalls: 0 },
  { toolId: 'tool-009', toolName: 'database_query', callCount: 3210, successCount: 3198, failureCount: 12, successRate: 99.6, avgDurationMs: 180, last24hCalls: 105 },
  { toolId: 'tool-010', toolName: 'api_call', callCount: 678, successCount: 601, failureCount: 77, successRate: 88.6, avgDurationMs: 2100, last24hCalls: 0 },
]

// ─── API 函数 ─────────────────────────────────────────────

/** 获取已注册工具列表 */
export async function fetchTools(): Promise<ToolInfo[]> {
  await delay()
  return [...mockTools]
}

/** 获取工具调用统计 */
export async function fetchToolStats(): Promise<ToolStats[]> {
  await delay()
  return [...mockStats]
}

/** 获取统计汇总 */
export async function fetchToolStatsSummary(): Promise<ToolStatsSummary> {
  await delay()
  return {
    totalTools: mockTools.length,
    activeTools: mockTools.filter((t) => t.status === 'active').length,
    totalCalls: mockStats.reduce((sum, s) => sum + s.callCount, 0),
    avgSuccessRate: Number((mockStats.reduce((sum, s) => sum + s.successRate, 0) / mockStats.length).toFixed(1)),
  }
}
