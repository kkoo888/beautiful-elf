/**
 * 操作日志 API 服务
 */

import { apiClient, extractData } from '@/services/api-client'
import type { ActionLog } from '../types/action-log'

export interface ActionLogListParams {
  page?: number; pageSize?: number; module?: string; action?: string; startTime?: string; endTime?: string
}

export interface ActionLogListResponse {
  data: ActionLog[]; total: number; page: number; pageSize: number
}

export interface CreateActionLogParams {
  module: string; action: string; paramsSummary: string; sessionId: string
}

export async function createActionLog(data: CreateActionLogParams): Promise<ActionLog> {
  return extractData(await apiClient.post('/action_logs', data))
}

export async function fetchActionLogs(params?: ActionLogListParams): Promise<ActionLogListResponse> {
  return extractData(await apiClient.get('/action_logs', { params })) as ActionLogListResponse
}

export async function cleanupActionLogs(days: number): Promise<void> {
  await apiClient.delete('/action_logs/cleanup', { params: { days } })
}
