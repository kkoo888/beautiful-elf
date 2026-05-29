import { apiClient } from '@/services/api-client'
import type { ActionLog } from '../types/action-log'

/** 操作日志列表查询参数 */
export interface ActionLogListParams {
  page?: number
  pageSize?: number
  module?: string
  action?: string
  startTime?: string
  endTime?: string
}

/** 操作日志列表响应 */
export interface ActionLogListResponse {
  data: ActionLog[]
  total: number
  page: number
  pageSize: number
}

/** 创建操作日志参数 */
export interface CreateActionLogParams {
  module: string
  action: string
  paramsSummary: string
  sessionId: string
}

/** 创建操作日志 */
export async function createActionLog(data: CreateActionLogParams): Promise<ActionLog> {
  const resp = await apiClient.post('/action_logs', data)
  return (resp.data as any).data
}

/** 获取操作日志列表 */
export async function fetchActionLogs(params?: ActionLogListParams): Promise<ActionLogListResponse> {
  const resp = await apiClient.get('/action_logs', { params })
  return (resp.data as any).data
}

/** 清理旧日志 */
export async function cleanupActionLogs(days: number): Promise<void> {
  await apiClient.delete('/action_logs/cleanup', { params: { days } })
}
