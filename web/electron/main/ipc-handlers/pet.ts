import { ipcMain } from 'electron'
import { getPetWindow, showPetWindow, hidePetWindow, isPetWindowVisible } from '../pet-window'

/** 转发模型切换通知到宠物窗口 */
function notifyPetWindowModelChanged(): void {
  const petWin = getPetWindow()
  if (petWin && !petWin.isDestroyed()) {
    petWin.webContents.send('pet:model-reload')
  }
}

/** 宠物窗口 IPC handlers */
export function registerPetHandlers(): void {
  // 显示宠物窗口 - 防御性创建 + 返回状态
  ipcMain.handle('pet:show', () => {
    const success = showPetWindow()
    return { success, visible: success ? true : isPetWindowVisible() }
  })

  // 隐藏宠物窗口 - 返回状态
  ipcMain.handle('pet:hide', () => {
    const success = hidePetWindow()
    return { success, visible: success ? false : isPetWindowVisible() }
  })

  // 切换宠物窗口 - 防御性创建 + 返回状态
  ipcMain.handle('pet:toggle', () => {
    const win = getPetWindow()
    if (!win || win.isDestroyed()) {
      // 窗口不存在或已销毁，创建并显示
      const success = showPetWindow()
      return { success, visible: true }
    }
    if (win.isVisible()) {
      hidePetWindow()
    } else {
      showPetWindow()
    }
    return { success: true, visible: win.isVisible() }
  })

  // 查询宠物窗口可见性
  ipcMain.handle('pet:isVisible', () => {
    return { success: true, visible: isPetWindowVisible() }
  })

  // 宠物属性查询 (超时5s)
  ipcMain.handle('pet:getAttributes', async () => {
    const win = getPetWindow()
    if (!win || win.isDestroyed()) {
      return { error: 'PET_WINDOW_ERROR', message: '宠物窗口未打开' }
    }
    try {
      return await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          // 超时后清理 once 监听器
          ipcMain.removeAllListeners('pet:attributes-response')
          reject(new Error('timeout'))
        }, 5000)

        ipcMain.once('pet:attributes-response', (_, data) => {
          clearTimeout(timeout)
          resolve(data)
        })

        win.webContents.send('pet:request-attributes')
      })
    } catch {
      return { error: 'PET_WINDOW_ERROR', message: '宠物窗口通信异常' }
    }
  })

  // 模型切换通知 (主窗口 → 宠物窗口)
  ipcMain.on('pet:model-changed', () => {
    notifyPetWindowModelChanged()
  })

  // 请求宠物窗口强制重载当前模型（刷新场景）
  ipcMain.handle('pet:reload', () => {
    const petWin = getPetWindow()
    if (!petWin || petWin.isDestroyed()) {
      return { success: false, error: 'PET_WINDOW_ERROR', message: '宠物窗口未打开' }
    }
    petWin.webContents.send('pet:force-reload')
    return { success: true }
  })

  // 缩放（放大缩小）：转发到宠物窗口
  ipcMain.handle('pet:zoom', (_e, factor: number) => {
    const petWin = getPetWindow()
    if (!petWin || petWin.isDestroyed()) {
      return { success: false, message: '宠物窗口未打开' }
    }
    petWin.webContents.send('pet:zoom', factor)
    return { success: true }
  })

  // 待机动画（动作）开关：转发到宠物窗口
  ipcMain.handle('pet:idle', (_e, enabled: boolean) => {
    const petWin = getPetWindow()
    if (!petWin || petWin.isDestroyed()) {
      return { success: false, message: '宠物窗口未打开' }
    }
    petWin.webContents.send('pet:idle', enabled)
    return { success: true }
  })

  // 重置缩放：转发到宠物窗口
  ipcMain.handle('pet:reset-zoom', () => {
    const petWin = getPetWindow()
    if (!petWin || petWin.isDestroyed()) {
      return { success: false, message: '宠物窗口未打开' }
    }
    petWin.webContents.send('pet:reset-zoom')
    return { success: true }
  })

  // 请求宠物窗口截图（主窗口 "截图" 按钮触发，转发到 pet 窗口）
  ipcMain.on('pet:request-screenshot', () => {
    const petWin = getPetWindow()
    if (petWin && !petWin.isDestroyed()) {
      petWin.webContents.send('pet:request-screenshot')
    }
  })

  // 拖动宠物窗口：按光标增量移动窗口位置
  ipcMain.on('pet:drag-window', (_e, dx: number, dy: number) => {
    const petWin = getPetWindow()
    if (!petWin || petWin.isDestroyed()) return
    const [x, y] = petWin.getPosition()
    petWin.setPosition(x + dx, y + dy)
  })
}
