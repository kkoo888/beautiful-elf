import { windowApi } from './windowApi'
import { appApi } from './appApi'
import { petApi } from './petApi'

/**
 * 聚合所有 API，暴露给渲染进程
 * 通过 contextBridge.exposeInMainWorld('electronAPI', api) 注入
 */
export const electronAPI = {
  window: windowApi,
  app: appApi,
  pet: petApi,
}

export type ElectronAPI = typeof electronAPI
