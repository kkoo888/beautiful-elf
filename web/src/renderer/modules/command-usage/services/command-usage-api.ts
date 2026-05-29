import { apiClient } from '@/services/api-client'
import type { CommandUsage } from '../types/command_usage'

/** 命令使用列表查询参数 */
export interface CommandUsageListParams {
  page?: number
  pageSize?: number
}

/** 命令使用列表响应 */
export interface CommandUsageListResponse {
  data: CommandUsage[]
  total: number
  page: number
  pageSize: number
}

/** 记录命令使用 */
export async function recordCommandUsage(commandId: number): Promise<CommandUsage> {
  const resp = await apiClient.post('/command_usage/record', null, { params: { commandId } })
  return (resp.data as any).data
}

/** 获取命令使用列表 */
export async function fetchCommandUsages(params?: CommandUsageListParams): Promise<CommandUsageListResponse> {
  const resp = await apiClient.get('/command_usage', { params })
  return (resp.data as any).data
}

/** 获取 Top N 命令 */
export async function fetchTopCommands(limit: number = 10): Promise<CommandUsage[]> {
  const resp = await apiClient.get('/command_usage/top', { params: { limit } })
  return (resp.data as any).data
}
