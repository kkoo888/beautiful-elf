/**
 * Electron API 类型声明
 * 为渲染进程提供 window.electronAPI 的类型提示
 */

interface WindowApi {
  minimize: () => Promise<void>
  maximize: () => Promise<void>
  close: () => Promise<void>
  isMaximized: () => Promise<boolean>
}

interface AppApi {
  getVersion: () => Promise<string>
}

interface PetApi {
  show: () => Promise<void>
  hide: () => Promise<void>
  toggle: () => Promise<void>
  getAttributes: () => Promise<Record<string, unknown>>
  onScreenshotUpdate: (callback: (data: string) => void) => void
  onVisibilityChange: (callback: (visible: boolean) => void) => void
  sendScreenshot: (data: string) => void
}

interface ElectronAPI {
  window: WindowApi
  app: AppApi
  pet: PetApi
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}

export {}
