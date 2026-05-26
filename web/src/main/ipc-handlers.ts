import { ipcMain, BrowserWindow } from 'electron'

export function registerIpcHandlers(): void {
  // 窗口控制
  ipcMain.handle('window:minimize', () => {
    BrowserWindow.getFocusedWindow()?.minimize()
  })

  ipcMain.handle('window:maximize', () => {
    const win = BrowserWindow.getFocusedWindow()
    if (win?.isMaximized()) {
      win.unmaximize()
    } else {
      win?.maximize()
    }
  })

  ipcMain.handle('window:close', () => {
    BrowserWindow.getFocusedWindow()?.close()
  })

  // 获取窗口状态
  ipcMain.handle('window:isMaximized', () => {
    return BrowserWindow.getFocusedWindow()?.isMaximized() ?? false
  })

  // 通知渲染进程
  ipcMain.handle('app:getVersion', () => {
    return process.env.npm_package_version || '0.1.0'
  })
}
