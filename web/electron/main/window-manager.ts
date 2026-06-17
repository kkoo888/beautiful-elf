import { BrowserWindow } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'
import { setPetVisibilityCallback } from './pet-window'

/**
 * 窗口管理器
 * 统一管理主窗口和宠物窗口的创建/销毁
 */

let mainWindow: BrowserWindow | null = null

/** 获取主窗口实例 */
export function getMainWindow(): BrowserWindow | null {
  return mainWindow
}

/** 创建主窗口 */
export function createMainWindow(): BrowserWindow {
  mainWindow = new BrowserWindow({
    width: 1980,
    height: 1080,
    minWidth: 900,
    minHeight: 600,
    show: false,
    title: 'Beautiful-Elf',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // 注入宠物窗口可见性回调（避免循环依赖）
  setPetVisibilityCallback((visible: boolean) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('pet:visibility-change', visible)
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // 加载页面
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  return mainWindow
}

/** 销毁所有窗口并退出 */
export function destroyAllWindows(): void {
  BrowserWindow.getAllWindows().forEach((win) => {
    if (!win.isDestroyed()) {
      win.destroy()
    }
  })
}
