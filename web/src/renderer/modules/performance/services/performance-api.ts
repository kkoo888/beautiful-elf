/**
 * 性能监控 API 服务
 * 后端 Query: limit
 */

import { apiClient, extractData } from '@/services/api-client'
import type { PerformanceMetric } from '../types/performance'

export async function fetchPerformanceMetrics(): Promise<PerformanceMetric[]> {
  const items = extractData(await apiClient.get('/performance/metrics', { params: { limit: 30 } })) as any[]
  return items.map((item) => ({
    cpu: item.cpuPercent, memory: item.memoryPercent, disk: item.diskPercent,
    gpu: item.gpuPercent ?? undefined, timestamp: item.createdAt,
  }))
}

export async function fetchCurrentStatus(): Promise<{
  cpuPercent: number; memoryPercent: number; memoryUsedMb: number; memoryTotalMb: number
  diskPercent: number; diskUsedGb: number; diskTotalGb: number; gpuPercent: number | null; uptimeSeconds: number
}> {
  return extractData(await apiClient.get('/performance/current')) as any
}
