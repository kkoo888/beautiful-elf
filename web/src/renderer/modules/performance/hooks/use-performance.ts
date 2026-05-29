/** 性能监控状态管理 hook（TanStack Query） */

import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import type { PerformanceMetric, PerformanceAlert, AlertThresholds } from '../types/performance'
import { DEFAULT_THRESHOLDS } from '../types/performance'
import { fetchPerformanceMetrics } from '../services/performance-api'

const METRICS_KEY = ['performance-metrics']

export interface UsePerformanceReturn {
  /** 最新指标数据 */
  latest: PerformanceMetric | undefined
  /** 全部历史数据 */
  metrics: PerformanceMetric[]
  /** 是否首次加载中（无数据时） */
  isLoading: boolean
  /** 是否正在刷新（后台轮询） */
  isFetching: boolean
  /** 错误信息 */
  error: Error | null
  /** 当前告警列表 */
  alerts: PerformanceAlert[]
  /** 是否存在告警 */
  hasAlerts: boolean
}

/** 计算告警列表 */
function computeAlerts(
  metric: PerformanceMetric | undefined,
  thresholds: AlertThresholds
): PerformanceAlert[] {
  if (!metric) return []

  const alerts: PerformanceAlert[] = []

  if (metric.cpu > thresholds.cpu) {
    alerts.push({
      type: 'cpu',
      value: metric.cpu,
      threshold: thresholds.cpu,
      timestamp: metric.timestamp,
    })
  }

  if (metric.memory > thresholds.memory) {
    alerts.push({
      type: 'memory',
      value: metric.memory,
      threshold: thresholds.memory,
      timestamp: metric.timestamp,
    })
  }

  if (metric.disk > thresholds.disk) {
    alerts.push({
      type: 'disk',
      value: metric.disk,
      threshold: thresholds.disk,
      timestamp: metric.timestamp,
    })
  }

  return alerts
}

/**
 * 性能监控数据 hook
 * @param thresholds 自定义告警阈值
 * @param pollInterval 轮询间隔（毫秒），默认 5000
 */
export function usePerformance(
  thresholds: AlertThresholds = DEFAULT_THRESHOLDS,
  pollInterval = 5000
): UsePerformanceReturn {
  const {
    data: metrics = [],
    isLoading,
    isFetching,
    error,
  } = useQuery({
    queryKey: METRICS_KEY,
    queryFn: fetchPerformanceMetrics,
    refetchInterval: pollInterval,
    staleTime: 0, // 始终认为是过期的，保证每次轮询都获取新数据
  })

  const latest = useMemo(() => {
    return metrics.length > 0 ? metrics[metrics.length - 1] : undefined
  }, [metrics])

  const alerts = useMemo(() => computeAlerts(latest, thresholds), [latest, thresholds])

  return {
    latest,
    metrics,
    isLoading,
    isFetching,
    error: error as Error | null,
    alerts,
    hasAlerts: alerts.length > 0,
  }
}
