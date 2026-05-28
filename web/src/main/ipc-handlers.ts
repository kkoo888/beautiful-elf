import { ipcMain, BrowserWindow } from 'electron'
import { getPetWindow } from './pet-window'
import { getMainWindow } from './window-manager'

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

  // ─── 宠物窗口控制 ───
  ipcMain.handle('pet:show', () => {
    getPetWindow()?.show()
  })

  ipcMain.handle('pet:hide', () => {
    getPetWindow()?.hide()
  })

  ipcMain.handle('pet:toggle', () => {
    const win = getPetWindow()
    if (win && !win.isDestroyed()) {
      if (win.isVisible()) {
        win.hide()
      } else {
        win.show()
      }
    }
  })

  // 宠物属性查询 (超时5s)
  ipcMain.handle('pet:getAttributes', async () => {
    const win = getPetWindow()
    if (!win || win.isDestroyed()) {
      return { error: 'PET_WINDOW_ERROR', message: '宠物窗口未打开' }
    }
    try {
      return await Promise.race([
        new Promise((resolve) => {
          win.webContents.send('pet:request-attributes')
          ipcMain.once('pet:attributes-response', (_, data) => resolve(data))
        }),
        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000)),
      ])
    } catch {
      return { error: 'PET_WINDOW_ERROR', message: '宠物窗口通信异常' }
    }
  })

  // 截图传输 (宠物窗口 → 主窗口)
  ipcMain.on('pet:screenshot', (_, data) => {
    const mainWin = getMainWindow()
    if (mainWin && !mainWin.isDestroyed()) {
      mainWin.webContents.send('pet:screenshot-update', data)
    }
  })
}
