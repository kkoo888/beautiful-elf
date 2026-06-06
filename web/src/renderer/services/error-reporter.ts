import type { ErrorInfo } from 'react'

export interface ErrorReport {
  message: string
  stack?: string
  componentStack?: string
  url: string
  userAgent: string
  timestamp: number
  module?: string
}

function truncate(str: string, maxLen: number): string {
  return str.length > maxLen ? str.slice(0, maxLen) + '...' : str
}

// 错误去重（同一错误 5 分钟内只上报一次）
const errorCache = new Map<string, number>()
const DEDUP_INTERVAL = 5 * 60 * 1000

function shouldReport(error: ErrorReport): boolean {
  const key = `${error.message}:${error.stack?.slice(0, 200)}`
  const last = errorCache.get(key)
  if (last && Date.now() - last < DEDUP_INTERVAL) return false
  errorCache.set(key, Date.now())
  return true
}

export async function reportError(error: any, info?: ErrorInfo, module?: string): Promise<void> {
  const report: ErrorReport = {
    message: truncate(error?.message || String(error), 500),
    stack: truncate(error?.stack || '', 2000),
    componentStack: truncate(info?.componentStack || '', 1000),
    url: window.location.href,
    userAgent: navigator.userAgent,
    timestamp: Date.now(),
    module,
  }

  if (!shouldReport(report)) return

  try {
    // 实际调用后端 API
    // await apiClient.post('/api/v1/errors', report)
    console.error('[ErrorReporter]', report)
  } catch {
    console.error('[ErrorReporter] Failed:', report)
  }
}
