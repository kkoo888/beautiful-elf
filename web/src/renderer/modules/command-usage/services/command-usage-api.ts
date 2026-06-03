/**
 * 命令使用 API 服务
 * 后端 Query: page, page_size, limit
 */

import { apiClient, extractData } from '@/services/api-client'
import type { CommandUsage } from '../types/command_usage'

export interface CommandUsageListParams { page?: number; pageSize?: number }
export interface CommandUsageListResponse { data: CommandUsage[]; total: number; page: number; pageSize: number }

export async function recordCommandUsage(commandId: number): Promise<CommandUsage> {
  return extractData(await apiClient.post('/command_usage/record', null, { params: { commandId } }))
}

export async function fetchCommandUsages(params?: CommandUsageListParams): Promise<CommandUsageListResponse> {
  return extractData(await apiClient.get('/command_usage', {
    params: { page: params?.page, page_size: params?.pageSize },
  })) as CommandUsageListResponse
}

export async function fetchTopCommands(limit: number = 10): Promise<CommandUsage[]> {
  return extractData(await apiClient.get('/command_usage/top', { params: { limit } }))
}
