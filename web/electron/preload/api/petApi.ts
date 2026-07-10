import { ipcRenderer } from 'electron'

/** 宠物窗口 API */
export const petApi = {
  show: () => ipcRenderer.invoke('pet:show'),
  hide: () => ipcRenderer.invoke('pet:hide'),
  toggle: () => ipcRenderer.invoke('pet:toggle'),
  isVisible: () => ipcRenderer.invoke('pet:isVisible'),
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
  /** 请求宠物窗口重新加载当前模型（刷新场景） */
  reload: () => ipcRenderer.invoke('pet:reload'),
  /** 相对缩放因子（放大缩小宠物） */
  zoom: (factor: number) => ipcRenderer.invoke('pet:zoom', factor),
  /** 设置待机动画（动作）开关 */
  setIdle: (enabled: boolean) => ipcRenderer.invoke('pet:idle', enabled),
  /** 重置缩放到 1 */
  resetZoom: () => ipcRenderer.invoke('pet:reset-zoom'),
  /** 拖动宠物窗口：按光标增量移动窗口位置（左键拖拽用） */
  dragWindowBy: (dx: number, dy: number) => ipcRenderer.send('pet:drag-window', dx, dy),
  /** 监听强制重载通知（刷新场景用），返回清理函数 */
  onForceReload: (callback: () => void): (() => void) => {
    const handler = () => callback()
    ipcRenderer.on('pet:force-reload', handler)
    return () => ipcRenderer.removeListener('pet:force-reload', handler)
  },
  /** 监听缩放指令（放大缩小），返回清理函数 */
  onZoom: (callback: (factor: number) => void): (() => void) => {
    const handler = (_: Electron.IpcRendererEvent, factor: number) => callback(factor)
    ipcRenderer.on('pet:zoom', handler)
    return () => ipcRenderer.removeListener('pet:zoom', handler)
  },
  /** 监听待机动画（动作）开关指令，返回清理函数 */
  onSetIdle: (callback: (enabled: boolean) => void): (() => void) => {
    const handler = (_: Electron.IpcRendererEvent, enabled: boolean) => callback(enabled)
    ipcRenderer.on('pet:idle', handler)
    return () => ipcRenderer.removeListener('pet:idle', handler)
  },
  /** 监听重置缩放指令，返回清理函数 */
  onResetZoom: (callback: () => void): (() => void) => {
    const handler = () => callback()
    ipcRenderer.on('pet:reset-zoom', handler)
    return () => ipcRenderer.removeListener('pet:reset-zoom', handler)
  },
  /** 监听全局鼠标移动（30fps，归一化坐标 -1~1），返回清理函数 */
  onGlobalMouseMove: (callback: (pos: { x: number; y: number }) => void): (() => void) => {
    const handler = (_: Electron.IpcRendererEvent, pos: { x: number; y: number }) => callback(pos)
    ipcRenderer.on('global-mouse-move', handler)
    return () => ipcRenderer.removeListener('global-mouse-move', handler)
  },
  /** 通知宠物窗口模型已切换，触发重新加载 */
  notifyModelChanged: () => {
    ipcRenderer.send('pet:model-changed')
  },
  /** 监听模型切换通知，返回清理函数 */
  onModelChanged: (callback: () => void): (() => void) => {
    const handler = () => callback()
    ipcRenderer.on('pet:model-reload', handler)
    return () => ipcRenderer.removeListener('pet:model-reload', handler)
  },
}
