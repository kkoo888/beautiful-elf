import { ipcMain } from 'electron'
import { getPetWindow } from '../pet-window'
import { getMainWindow } from '../window-manager'

/** 宠物窗口 IPC handlers */
export function registerPetHandlers(): void {
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
