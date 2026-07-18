import { ipcRenderer } from 'electron'

export const worldApi = {
  show: () => ipcRenderer.invoke('world:show'),
  hide: () => ipcRenderer.invoke('world:hide'),
  toggle: () => ipcRenderer.invoke('world:toggle'),
  isVisible: () => ipcRenderer.invoke('world:isVisible'),
  reload: () => ipcRenderer.invoke('world:reload'),
  requestScreenshot: () => ipcRenderer.send('world:request-screenshot'),
  onVisibilityChange: (callback: (visible: boolean) => void): (() => void) => {
    const handler = (_: Electron.IpcRendererEvent, visible: boolean) => callback(visible)
    ipcRenderer.on('world:visibility-change', handler)
    return () => ipcRenderer.removeListener('world:visibility-change', handler)
  },
}
