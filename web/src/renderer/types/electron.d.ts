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
  /** 监听截图更新，返回清理函数 */
  onScreenshotUpdate: (callback: (data: string) => void) => (() => void)
  /** 监听可见性变化，返回清理函数 */
  onVisibilityChange: (callback: (visible: boolean) => void) => (() => void)
  sendScreenshot: (data: string) => void
  /** 通知宠物窗口模型已切换，触发重新加载 */
  notifyModelChanged: () => void
  /** 监听模型切换通知，返回清理函数 */
  onModelChanged: (callback: () => void) => (() => void)
}

interface DialogApi {
  selectDirectory: () => Promise<string | null>
}

interface DesktopCapturerSource {
  id: string
  name: string
  thumbnail: string // data URL
}

interface DesktopCapturerApi {
  getSources: (options: { types: Array<'screen' | 'window'> }) => Promise<DesktopCapturerSource[]>
}

interface ElectronAPI {
  window: WindowApi
  app: AppApi
  pet: PetApi
  dialog: DialogApi
  desktopCapturer: DesktopCapturerApi
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}

export {}
