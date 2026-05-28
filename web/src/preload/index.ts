import { contextBridge, ipcRenderer } from 'electron'

const api = {
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:isMaximized')
  },
  app: {
    getVersion: () => ipcRenderer.invoke('app:getVersion')
  },
  pet: {
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
    }
  }
}

contextBridge.exposeInMainWorld('electronAPI', api)

export type ElectronAPI = typeof api
