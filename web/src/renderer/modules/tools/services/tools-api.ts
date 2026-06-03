/**
 * 工具管理 API 服务
 *
 * 后端 Query 参数: page, page_size, is_enabled → snake_case
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  ToolInfo, ToolStats, ToolStatsSummary, ToolQueryParams,
  CreateToolInput, UpdateToolInput, PaginatedResult,
} from '../types/tools'

export async function fetchTools(params?: ToolQueryParams): Promise<PaginatedResult<ToolInfo>> {
  const resp = await apiClient.get('/tools', {
    params: { page: params?.page ?? 1, page_size: params?.pageSize ?? 20, is_enabled: params?.isEnabled },
  })
  const { items, total, page, pageSize } = extractPaginated(resp as any)
  return { data: items, total, page, pageSize }
}

export async function createTool(input: CreateToolInput): Promise<ToolInfo> {
  return extractData(await apiClient.post('/tools', input))
}

export async function updateTool(id: string, input: UpdateToolInput): Promise<ToolInfo> {
  return extractData(await apiClient.put(`/tools/${id}`, input))
}

export async function deleteTool(id: string): Promise<void> {
  await apiClient.delete(`/tools/${id}`)
}

export async function enableTool(id: string): Promise<ToolInfo> {
  return extractData(await apiClient.patch(`/tools/${id}/enable`))
}

export async function disableTool(id: string): Promise<ToolInfo> {
  return extractData(await apiClient.patch(`/tools/${id}/disable`))
}

export async function fetchToolStats(id: string): Promise<ToolStats> {
  return extractData(await apiClient.get(`/tools/${id}/stats`))
}

export async function recordToolCall(id: string, success: boolean, durationMs: number): Promise<void> {
  await apiClient.post(`/tools/${id}/stats/record`, null, { params: { success, duration_ms: durationMs } })
}

export async function fetchToolStatsSummary(): Promise<ToolStatsSummary> {
  return extractData(await apiClient.get('/tools/stats/summary'))
}
