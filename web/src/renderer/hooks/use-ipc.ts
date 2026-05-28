import { useCallback } from 'react'
import { z } from 'zod'

/**
 * 类型安全的 IPC 调用 Hook
 * 使用 Zod schema 校验返回值类型
 */
export function useIPC() {
  const isElectron = typeof window !== 'undefined' && window.electronAPI !== undefined

  const invoke = useCallback(
    async <T>(channel: string, schema: z.ZodType<T>, ...args: unknown[]): Promise<T> => {
      if (!isElectron) {
        throw new Error('[useIPC] Not in Electron environment')
      }

      const api = window.electronAPI as Record<string, Record<string, (...a: unknown[]) => unknown>>
      const [namespace, method] = channel.split(':')

      if (!api[namespace] || typeof api[namespace][method] !== 'function') {
        throw new Error(`[useIPC] Unknown channel: ${channel}`)
      }

      const result = await api[namespace][method](...args)
      return schema.parse(result)
    },
    [isElectron]
  )

  const send = useCallback(
    (channel: string, ...args: unknown[]) => {
      if (!isElectron) {
        console.warn('[useIPC] Not in Electron environment')
        return
      }

      const api = window.electronAPI as Record<string, Record<string, (...a: unknown[]) => unknown>>
      const [namespace, method] = channel.split(':')

      if (api[namespace] && typeof api[namespace][method] === 'function') {
        api[namespace][method](...args)
      }
    },
    [isElectron]
  )

  const on = useCallback(
    (channel: string, callback: (...args: unknown[]) => void): (() => void) => {
      if (!isElectron) {
        console.warn('[useIPC] Not in Electron environment')
        return () => {}
      }

      const api = window.electronAPI as Record<
        string,
        Record<string, ((...a: unknown[]) => unknown) | undefined>
      >
      const [namespace, method] = channel.split(':')

      if (api[namespace] && typeof api[namespace][method] === 'function') {
        return (api[namespace][method] as (...a: unknown[]) => unknown)(callback) as () => void
      }

      return () => {}
    },
    [isElectron]
  )

  return { isElectron, invoke, send, on }
}
