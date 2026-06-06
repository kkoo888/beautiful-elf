import { ipcRenderer } from 'electron'

/** 宠物窗口 API */
export const petApi = {
  show: () => ipcRenderer.invoke('pet:show'),
  hide: () => ipcRenderer.invoke('pet:hide'),
  toggle: () => ipcRenderer.invoke('pet:toggle'),
  getAttributes: () => ipcRenderer.invoke('pet:getAttributes'),
  /** 监听截图更新，返回清理函数 */
  onScreenshotUpdate: (callback: (data: string) => void): (() => void) => {
    const handler = (_: Electron.IpcRendererEvent, data: string) => callback(data)
    ipcRenderer.on('pet:screenshot-update', handler)
    return () => ipcRenderer.removeListener('pet:screenshot-update', handler)
  },
  /** 监听可见性变化，返回清理函数 */
  onVisibilityChange: (callback: (visible: boolean) => void): (() => void) => {
    const handler = (_: Electron.IpcRendererEvent, visible: boolean) => callback(visible)
    ipcRenderer.on('pet:visibility-change', handler)
    return () => ipcRenderer.removeListener('pet:visibility-change', handler)
  },
  sendScreenshot: (data: string) => {
    ipcRenderer.send('pet:screenshot', data)
  },
}
