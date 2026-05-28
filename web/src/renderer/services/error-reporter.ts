import type { ErrorInfo } from 'react'
import { apiClient } from './api-client'

/**
 * 全局错误上报
 * 将前端错误发送到后端 /api/v1/errors 接口
 */
export async function reportError(
  error: Error | null | undefined,
  info?: ErrorInfo
): Promise<void> {
  try {
    await apiClient.post('/api/v1/errors', {
      message: error?.message || String(error),
      stack: error?.stack?.slice(0, 2000),
      componentStack: info?.componentStack?.slice(0, 1000),
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: Date.now(),
    })
  } catch {
    // 上报失败静默处理
    console.error('[ErrorReporter] Failed to report error:', error)
  }
}
