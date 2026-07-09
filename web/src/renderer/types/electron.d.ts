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
  show: () => Promise<{ success: boolean; visible: boolean }>
  hide: () => Promise<{ success: boolean; visible: boolean }>
  toggle: () => Promise<{ success: boolean; visible: boolean }>
  isVisible: () => Promise<{ success: boolean; visible: boolean }>
  getAttributes: () => Promise<Record<string, unknown>>
  /** 请求宠物窗口重新加载当前模型 */
  reload: () => Promise<{ success: boolean; message?: string }>
  /** 监听截图更新，返回清理函数 */
  onScreenshotUpdate: (callback: (data: string) => void) => (() => void)
  /** 监听可见性变化，返回清理函数 */
  onVisibilityChange: (callback: (visible: boolean) => void) => (() => void)
  sendScreenshot: (data: string) => void
  /** 通知宠物窗口模型已切换，触发重新加载 */
  notifyModelChanged: () => void
  /** 监听模型切换通知（路径变更），返回清理函数 */
  onModelChanged: (callback: () => void) => (() => void)
  /** 监听强制重载通知（刷新场景），返回清理函数 */
  onForceReload: (callback: () => void) => (() => void)
  /** 监听全局鼠标移动（30fps，归一化坐标 -1~1），返回清理函数 */
  onGlobalMouseMove: (callback: (pos: { x: number; y: number }) => void) => (() => void)
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
