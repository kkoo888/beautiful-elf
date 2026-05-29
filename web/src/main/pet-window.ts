import { BrowserWindow, screen } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'

let petWindow: BrowserWindow | null = null

export function createPetWindow(): BrowserWindow {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  petWindow = new BrowserWindow({
    width: 400,
    height: 500,
    x: width - 420,
    y: height - 520,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    hasShadow: false,
    show: false, // 默认隐藏，用户手动打开
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: join(__dirname, '../preload/index.js'),
    },
  })

  // 加载宠物窗口页面
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    petWindow.loadURL(`${process.env['ELECTRON_RENDERER_URL']}/pet-window.html`)
  } else {
    petWindow.loadFile(join(__dirname, '../renderer/pet-window.html'))
  }

  // 性能自适应：不可见时降帧
  petWindow.on('hide', () => {
    if (petWindow && !petWindow.isDestroyed()) {
      petWindow.webContents.send('pet:visibility-change', false)
    }
  })
  petWindow.on('show', () => {
    if (petWindow && !petWindow.isDestroyed()) {
      petWindow.webContents.send('pet:visibility-change', true)
    }
  })

  // 窗口关闭处理
  petWindow.on('closed', () => {
    petWindow = null
  })

  return petWindow
}

export function getPetWindow(): BrowserWindow | null {
  return petWindow
}

export function destroyPetWindow(): void {
  if (petWindow && !petWindow.isDestroyed()) {
    petWindow.destroy()
    petWindow = null
  }
}
