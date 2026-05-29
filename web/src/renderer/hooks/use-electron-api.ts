import { useMemo } from 'react'

/**
 * 封装 window.electronAPI 调用
 * 提供类型安全 + 环境检测 + 优雅降级
 */
export function useElectronApi() {
  const isElectron = typeof window !== 'undefined' && window.electronAPI !== undefined

  const windowApi = useMemo(
    () => ({
      minimize: async () => {
        if (isElectron) await window.electronAPI.window.minimize()
      },
      maximize: async () => {
        if (isElectron) await window.electronAPI.window.maximize()
      },
      close: async () => {
        if (isElectron) await window.electronAPI.window.close()
      },
      isMaximized: async (): Promise<boolean> => {
        if (isElectron) return window.electronAPI.window.isMaximized()
        return false
      },
    }),
    [isElectron]
  )

  const appApi = useMemo(
    () => ({
      getVersion: async (): Promise<string> => {
        if (isElectron) return window.electronAPI.app.getVersion()
        return 'unknown'
      },
    }),
    [isElectron]
  )

  const petApi = useMemo(
    () => ({
      show: async () => {
        if (isElectron) await window.electronAPI.pet.show()
      },
      hide: async () => {
        if (isElectron) await window.electronAPI.pet.hide()
      },
      toggle: async () => {
        if (isElectron) await window.electronAPI.pet.toggle()
      },
      getAttributes: async () => {
        if (isElectron) return window.electronAPI.pet.getAttributes()
        return null
      },
      onScreenshotUpdate: (callback: (data: string) => void): (() => void) => {
        if (isElectron) return window.electronAPI.pet.onScreenshotUpdate(callback)
        return () => {}
      },
      onVisibilityChange: (callback: (visible: boolean) => void): (() => void) => {
        if (isElectron) return window.electronAPI.pet.onVisibilityChange(callback)
        return () => {}
      },
      sendScreenshot: (data: string) => {
        if (isElectron) window.electronAPI.pet.sendScreenshot(data)
      },
    }),
    [isElectron]
  )

  const dialogApi = useMemo(
    () => ({
      selectDirectory: async (): Promise<string | null> => {
        if (isElectron && window.electronAPI.dialog) {
          return window.electronAPI.dialog.selectDirectory()
        }
        return null
      },
    }),
    [isElectron]
  )

  return { isElectron, window: windowApi, app: appApi, pet: petApi, dialog: dialogApi }
}
