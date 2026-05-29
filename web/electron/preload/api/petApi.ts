import { ipcRenderer } from 'electron'

/** 宠物窗口 API */
export const petApi = {
  show: () => ipcRenderer.invoke('pet:show'),
  hide: () => ipcRenderer.invoke('pet:hide'),
  toggle: () => ipcRenderer.invoke('pet:toggle'),
  getAttributes: () => ipcRenderer.invoke('pet:getAttributes'),
  onScreenshotUpdate: (callback: (data: string) => void) => {
    ipcRenderer.on('pet:screenshot-update', (_, data) => callback(data))
  },
  onVisibilityChange: (callback: (visible: boolean) => void) => {
    ipcRenderer.on('pet:visibility-change', (_, visible) => callback(visible))
  },
  sendScreenshot: (data: string) => {
    ipcRenderer.send('pet:screenshot', data)
  },
}
