import { ipcRenderer } from 'electron'

/** 应用信息 API */
export const appApi = {
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
}
