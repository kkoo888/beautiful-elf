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
 * camelCase 转 snake_case（深层递归，支持数组）
 */
export function camelToSnake(obj: unknown): unknown {
  if (Array.isArray(obj)) return obj.map(camelToSnake)
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [
        k.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`),
        camelToSnake(v),
      ])
    )
  }
  return obj
}

/**
 * snake_case 转 camelCase（深层递归，支持数组）
 */
export function snakeToCamel(obj: unknown): unknown {
  if (Array.isArray(obj)) return obj.map(snakeToCamel)
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [
        k.replace(/_([a-z])/g, (_, c) => c.toUpperCase()),
        snakeToCamel(v),
      ])
    )
  }
  return obj
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
