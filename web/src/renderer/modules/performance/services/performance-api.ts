/**
 * 性能监控 API 服务
 *
 * 后端 CamelModel 已统一返回 camelCase，直接透传。
 * 前端 PerformanceMetric 做字段精简映射（只保留需要的字段）。
 */

import { apiClient } from '@/services/api-client'
import type { PerformanceMetric } from '../types/performance'

/** 获取历史性能指标 */
export async function fetchPerformanceMetrics(): Promise<PerformanceMetric[]> {
  const resp = await apiClient.get('/performance/metrics', { params: { limit: 30 } })
  const body = resp.data as any
  const items: any[] = body.data ?? []
  return items.map((item) => ({
    cpu: item.cpuPercent,
    memory: item.memoryPercent,
    disk: item.diskPercent,
    gpu: item.gpuPercent ?? undefined,
    timestamp: item.createdAt,
  }))
}

/** 获取当前系统状态 */
export async function fetchCurrentStatus(): Promise<{
  cpuPercent: number
  memoryPercent: number
  memoryUsedMb: number
  memoryTotalMb: number
  diskPercent: number
  diskUsedGb: number
  diskTotalGb: number
  gpuPercent: number | null
  uptimeSeconds: number
}> {
  const resp = await apiClient.get('/performance/current')
  return (resp.data as any).data
}
