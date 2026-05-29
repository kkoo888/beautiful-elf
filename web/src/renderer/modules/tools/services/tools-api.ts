/** 工具管理 API 服务 */

import { apiClient } from '@/services/api-client'
import type {
  ToolInfo,
  ToolStats,
  ToolQueryParams,
  CreateToolInput,
  UpdateToolInput,
  PaginatedResult,
} from '../types/tools'

/** 获取工具列表（分页） */
export async function fetchTools(params?: ToolQueryParams): Promise<PaginatedResult<ToolInfo>> {
  const resp = await apiClient.get('/tools', { params: { page: params?.page ?? 1, pageSize: params?.pageSize ?? 20, enabled: params?.enabled } })
  const body = resp.data as any
  return {
    data: body.data,
    total: body.total,
    page: body.page,
    pageSize: body.pageSize,
  }
}

/** 创建工具 */
export async function createTool(input: CreateToolInput): Promise<ToolInfo> {
  const resp = await apiClient.post('/tools', input)
  return (resp.data as any).data
}

/** 更新工具 */
export async function updateTool(id: string, input: UpdateToolInput): Promise<ToolInfo> {
  const resp = await apiClient.put(`/tools/${id}`, input)
  return (resp.data as any).data
}

/** 删除工具 */
export async function deleteTool(id: string): Promise<void> {
  await apiClient.delete(`/tools/${id}`)
}

/** 启用工具 */
export async function enableTool(id: string): Promise<ToolInfo> {
  const resp = await apiClient.patch(`/tools/${id}/enable`)
  return (resp.data as any).data
}

/** 禁用工具 */
export async function disableTool(id: string): Promise<ToolInfo> {
  const resp = await apiClient.patch(`/tools/${id}/disable`)
  return (resp.data as any).data
}

/** 获取工具统计 */
export async function fetchToolStats(id: string): Promise<ToolStats> {
  const resp = await apiClient.get(`/tools/${id}/stats`)
  return (resp.data as any).data
}

/** 记录工具调用 */
export async function recordToolCall(id: string, success: boolean, durationMs: number): Promise<void> {
  await apiClient.post(`/tools/${id}/stats/record`, null, {
    params: { success, durationMs },
  })
}
