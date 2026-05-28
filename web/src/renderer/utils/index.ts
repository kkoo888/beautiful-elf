/**
 * 工具函数统一导出
 */

export { cn } from './cn'
export {
  formatDate,
  formatRelativeTime,
  formatNumber,
  formatFileSize,
  formatPercent,
  formatDuration,
} from './format'
export { encrypt, decrypt } from './crypto'

/**
 * camelCase 转 snake_case（深层递归）
 */
export function camelToSnake(obj: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => {
      const snakeKey = k.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)
      // 递归处理嵌套对象
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        return [snakeKey, camelToSnake(v as Record<string, unknown>)]
      }
      return [snakeKey, v]
    })
  )
}

/**
 * snake_case 转 camelCase（深层递归）
 */
export function snakeToCamel(obj: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => {
      const camelKey = k.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
      // 递归处理嵌套对象
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        return [camelKey, snakeToCamel(v as Record<string, unknown>)]
      }
      return [camelKey, v]
    })
  )
}

/**
 * 生成 UUID
 */
export function generateId(): string {
  return crypto.randomUUID()
}

/**
 * 延迟
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * 截断字符串
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength) + '...'
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args)
      inThrottle = true
      setTimeout(() => {
        inThrottle = false
      }, limit)
    }
  }
}
