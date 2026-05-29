import { apiClient } from '@/services/api-client'
import type { PerformanceMetric } from '../types/performance'

// ── 类型映射：后端 → 前端 ─────────────────────────────────────

interface BackendMetric {
  id: number
  cpu_percent: number
  memory_percent: number
  memory_used_mb: number
  disk_percent: number
  disk_used_gb: number
  gpu_percent: number | null
  created_at: string
}

interface BackendCurrentStatus {
  cpu_percent: number
  memory_percent: number
  memory_used_mb: number
  memory_total_mb: number
  disk_percent: number
  disk_used_gb: number
  disk_total_gb: number
  gpu_percent: number | null
  uptime_seconds: number
}

function toFrontendMetric(item: BackendMetric): PerformanceMetric {
  return {
    cpu: item.cpu_percent,
    memory: item.memory_percent,
    disk: item.disk_percent,
    gpu: item.gpu_percent ?? undefined,
    timestamp: item.created_at,
  }
}

// ── API 函数 ──────────────────────────────────────────────────

/** 获取历史性能指标 */
export async function fetchPerformanceMetrics(): Promise<PerformanceMetric[]> {
  const resp = await apiClient.get('/performance/metrics', { params: { limit: 30 } })
  const body = resp.data as any
  const items: BackendMetric[] = body.data ?? []
  return items.map(toFrontendMetric)
}

/** 获取当前系统状态 */
export async function fetchCurrentStatus(): Promise<BackendCurrentStatus> {
  const resp = await apiClient.get('/performance/current')
  return (resp.data as any).data
}
