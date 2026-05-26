import { useCallback } from 'react'

/**
 * Electron IPC 调用 Hook
 */
export function useIPC() {
  const isElectron = typeof window !== 'undefined' && window.electronAPI !== undefined

  const invoke = useCallback(async <T>(channel: string, ...args: unknown[]): Promise<T | null> => {
    if (!isElectron) {
      console.warn('[useIPC] Not in Electron environment')
      return null
    }

    try {
      const api = window.electronAPI as Record<string, Record<string, (...a: unknown[]) => unknown>>
      const [namespace, method] = channel.split(':')
      if (api[namespace] && typeof api[namespace][method] === 'function') {
        return await api[namespace][method](...args)
      }
      console.warn(`[useIPC] Unknown channel: ${channel}`)
      return null
    } catch (error) {
      console.error(`[useIPC] Error invoking ${channel}:`, error)
      return null
    }
  }, [isElectron])

  // 窗口操作
  const minimizeWindow = useCallback(() => invoke('window:minimize'), [invoke])
  const maximizeWindow = useCallback(() => invoke('window:maximize'), [invoke])
  const closeWindow = useCallback(() => invoke('window:close'), [invoke])
  const isMaximized = useCallback(() => invoke<boolean>('window:isMaximized'), [invoke])
  const getAppVersion = useCallback(() => invoke<string>('app:getVersion'), [invoke])

  return {
    isElectron,
    invoke,
    minimizeWindow,
    maximizeWindow,
    closeWindow,
    isMaximized,
    getAppVersion
  }
}
