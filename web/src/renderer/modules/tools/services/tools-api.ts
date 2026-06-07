/**
 * 工具管理 API 服务
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type {
  ToolInfo, ToolStats, ToolQueryParams,
  CreateToolInput, UpdateToolInput,
} from '../types/tools'

export async function fetchTools(params?: ToolQueryParams): Promise<ToolInfo[]> {
  const resp = await apiClient.get('/tools', {
    params: { page: params?.page ?? 1, pageSize: params?.pageSize ?? 20, enabled: params?.isEnabled },
  })
  const { items } = extractPaginated(resp as any)
  return items
}

export async function createTool(input: CreateToolInput): Promise<ToolInfo> {
  return extractData(await apiClient.post('/tools', input))
}

export async function updateTool(id: number, input: UpdateToolInput): Promise<ToolInfo> {
  return extractData(await apiClient.put(`/tools/${id}`, input))
}

export async function deleteTool(id: number): Promise<void> {
  await apiClient.delete(`/tools/${id}`)
}

export async function enableTool(id: number): Promise<ToolInfo> {
  return extractData(await apiClient.patch(`/tools/${id}/enable`))
}

export async function disableTool(id: number): Promise<ToolInfo> {
  return extractData(await apiClient.patch(`/tools/${id}/disable`))
}

export async function fetchToolStats(id: number): Promise<ToolStats> {
  return extractData(await apiClient.get(`/tools/${id}/stats`))
}

export async function recordToolCall(id: number, success: boolean, durationMs: number): Promise<void> {
  await apiClient.post(`/tools/${id}/stats/record`, null, { params: { success, durationMs } })
}
