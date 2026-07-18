import { ipcMain } from 'electron'
import {
  getWorldWindow, createWorldWindow, showWorldWindow, hideWorldWindow, isWorldWindowVisible,
} from '../world-window'

export function registerWorldHandlers(): void {
  // 窗口控制
  ipcMain.handle('world:show', () => {
    createWorldWindow()
    showWorldWindow()
    return { success: true }
  })

  ipcMain.handle('world:hide', () => {
    hideWorldWindow()
    return { success: true }
  })

  ipcMain.handle('world:toggle', () => {
    if (isWorldWindowVisible()) {
      hideWorldWindow()
      return { success: true, visible: false }
    }
    createWorldWindow()
    showWorldWindow()
    return { success: true, visible: true }
  })

  ipcMain.handle('world:isVisible', () => {
    return { success: true, visible: isWorldWindowVisible() }
  })

  ipcMain.handle('world:reload', () => {
    const win = getWorldWindow()
    if (win && !win.isDestroyed()) {
      win.reload()
      return { success: true }
    }
    return { success: false, message: '窗口未打开' }
  })

  // 截图请求（转发到渲染进程）
  ipcMain.on('world:request-screenshot', () => {
    const win = getWorldWindow()
    if (win && !win.isDestroyed()) {
      win.webContents.send('world:request-screenshot')
    }
  })

  // 可见性变化通知
  ipcMain.on('world:visibility-change', (_, visible: boolean) => {
    // 广播给所有窗口
    const win = getWorldWindow()
    if (win && !win.isDestroyed()) {
      win.webContents.send('world:visibility-change', visible)
    }
  })
}
