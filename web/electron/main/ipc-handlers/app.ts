import { ipcMain } from 'electron'

/** 应用信息 IPC handlers */
export function registerAppHandlers(): void {
  ipcMain.handle('app:getVersion', () => {
    return process.env.npm_package_version || '0.1.0'
  })
}
