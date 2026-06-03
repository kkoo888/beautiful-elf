/**
 * 工具管理 API 服务
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  ToolInfo,
  ToolStats,
  ToolStatsSummary,
  ToolQueryParams,
  CreateToolInput,
  UpdateToolInput,
  PaginatedResult,
} from '../types/tools'

/** 获取工具列表（分页） */
export async function fetchTools(params?: ToolQueryParams): Promise<PaginatedResult<ToolInfo>> {
  const resp = await apiClient.get('/tools', {
    params: { page: params?.page ?? 1, pageSize: params?.pageSize ?? 20, isEnabled: params?.isEnabled },
  })
  const { items, total, page, pageSize } = extractPaginated(resp as any)
  return { data: items, total, page, pageSize }
}

/** 创建工具 */
export async function createTool(input: CreateToolInput): Promise<ToolInfo> {
  return extractData(await apiClient.post('/tools', input))
}

/** 更新工具 */
export async function updateTool(id: string, input: UpdateToolInput): Promise<ToolInfo> {
  return extractData(await apiClient.put(`/tools/${id}`, input))
}

/** 删除工具 */
export async function deleteTool(id: string): Promise<void> {
  await apiClient.delete(`/tools/${id}`)
}

/** 启用工具 */
export async function enableTool(id: string): Promise<ToolInfo> {
  return extractData(await apiClient.patch(`/tools/${id}/enable`))
}

/** 禁用工具 */
export async function disableTool(id: string): Promise<ToolInfo> {
  return extractData(await apiClient.patch(`/tools/${id}/disable`))
}

/** 获取工具统计 */
export async function fetchToolStats(id: string): Promise<ToolStats> {
  return extractData(await apiClient.get(`/tools/${id}/stats`))
}

/** 记录工具调用 */
export async function recordToolCall(id: string, success: boolean, durationMs: number): Promise<void> {
  await apiClient.post(`/tools/${id}/stats/record`, null, {
    params: { success, durationMs },
  })
}

/** 获取工具统计汇总 */
export async function fetchToolStatsSummary(): Promise<ToolStatsSummary> {
  return extractData(await apiClient.get('/tools/stats/summary'))
}
