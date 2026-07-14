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
        if (isElectron) return window.electronAPI.pet.toggle()
        return { success: false, visible: false }
      },
      isVisible: async (): Promise<{ success: boolean; visible: boolean }> => {
        if (isElectron) return window.electronAPI.pet.isVisible()
        return { success: false, visible: false }
      },
      getAttributes: async () => {
        if (isElectron) return window.electronAPI.pet.getAttributes()
        return null
      },
      requestScreenshot: () => {
        if (isElectron) window.electronAPI.pet.requestScreenshot()
      },
      onRequestScreenshot: (callback: () => void): (() => void) => {
        if (isElectron) return window.electronAPI.pet.onRequestScreenshot(callback)
        return () => {}
      },
      onVisibilityChange: (callback: (visible: boolean) => void): (() => void) => {
        if (isElectron) return window.electronAPI.pet.onVisibilityChange(callback)
        return () => {}
      },

      reload: async (): Promise<{ success: boolean; message?: string }> => {
        if (isElectron) return window.electronAPI.pet.reload()
        return { success: false, message: '非 Electron 环境' }
      },
      zoom: async (factor: number): Promise<{ success: boolean; message?: string }> => {
        if (isElectron) return window.electronAPI.pet.zoom(factor)
        return { success: false, message: '非 Electron 环境' }
      },
      setIdle: async (enabled: boolean): Promise<{ success: boolean; message?: string }> => {
        if (isElectron) return window.electronAPI.pet.setIdle(enabled)
        return { success: false, message: '非 Electron 环境' }
      },
      resetZoom: async (): Promise<{ success: boolean; message?: string }> => {
        if (isElectron) return window.electronAPI.pet.resetZoom()
        return { success: false, message: '非 Electron 环境' }
      },
      dragWindowBy: (dx: number, dy: number): void => {
        if (isElectron) window.electronAPI.pet.dragWindowBy(dx, dy)
      },
      notifyModelChanged: () => {
        if (isElectron) window.electronAPI.pet.notifyModelChanged()
      },
      onModelChanged: (callback: () => void): (() => void) => {
        if (isElectron) return window.electronAPI.pet.onModelChanged(callback)
        return () => {}
      },
      onForceReload: (callback: () => void): (() => void) => {
        if (isElectron) return window.electronAPI.pet.onForceReload(callback)
        return () => {}
      },
      onGlobalMouseMove: (callback: (pos: { x: number; y: number }) => void): (() => void) => {
        if (isElectron) return window.electronAPI.pet.onGlobalMouseMove(callback)
        return () => {}
      },
    }),
    [isElectron]
  )

  const dialogApi = useMemo(
    () => ({
      selectDirectory: async (): Promise<string | null> => {
        if (isElectron) return window.electronAPI.dialog.selectDirectory()
        return null
      },
    }),
    [isElectron]
  )

  return { isElectron, window: windowApi, app: appApi, pet: petApi, dialog: dialogApi }
}
