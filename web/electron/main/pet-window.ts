import { BrowserWindow, screen } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'

let petWindow: BrowserWindow | null = null

/** 外部注入的可见性变化回调（由 window-manager 设置，避免循环依赖） */
let visibilityCallback: ((visible: boolean) => void) | null = null

export function setPetVisibilityCallback(cb: (visible: boolean) => void): void {
  visibilityCallback = cb
}

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
    show: false,
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
    // 通知外部：宠物窗口已隐藏（通过回调注入，避免循环依赖）
    visibilityCallback?.(false)
  })
  petWindow.on('show', () => {
    if (petWindow && !petWindow.isDestroyed()) {
      petWindow.webContents.send('pet:visibility-change', true)
    }
    // 通知外部：宠物窗口已显示（通过回调注入，避免循环依赖）
    visibilityCallback?.(true)
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

/**
 * 安全显示宠物窗口
 * 如果窗口不存在或已销毁，自动创建
 * @returns 操作是否成功
 */
export function showPetWindow(): boolean {
  let win = getPetWindow()
  if (!win || win.isDestroyed()) {
    win = createPetWindow()
  }
  if (win && !win.isDestroyed()) {
    win.show()
    return true
  }
  return false
}

/**
 * 安全隐藏宠物窗口
 * @returns 操作是否成功
 */
export function hidePetWindow(): boolean {
  const win = getPetWindow()
  if (win && !win.isDestroyed()) {
    win.hide()
    return true
  }
  return false
}

/**
 * 查询宠物窗口是否可见
 * @returns 可见状态，窗口不存在时返回 false
 */
export function isPetWindowVisible(): boolean {
  const win = getPetWindow()
  return win ? win.isVisible() : false
}
