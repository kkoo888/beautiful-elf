import { BrowserWindow, screen } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'

let petWindow: BrowserWindow | null = null

/** 外部注入的可见性变化回调（由 window-manager 设置，避免循环依赖） */
let visibilityCallback: ((visible: boolean) => void) | null = null

/** 鼠标追踪定时器 */
let mouseTrackInterval: ReturnType<typeof setInterval> | null = null

/** 鼠标追踪脏标记状态 */
let _lastMouseX = 0
let _lastMouseY = 0
const MOUSE_MOVE_THRESHOLD = 0.002 // 归一化坐标变化阈值，低于此值不发送 IPC

/** 启动 1fps 鼠标追踪（仅在鼠标实际移动时发送 IPC） */
function startMouseTracking(): void {
  if (mouseTrackInterval) return
  // 重置脏标记，避免恢复显示时发送过期坐标
  _lastMouseX = NaN
  _lastMouseY = NaN
  mouseTrackInterval = setInterval(() => {
    if (!petWindow || petWindow.isDestroyed()) {
      stopMouseTracking()
      return
    }
    try {
      const cursor = screen.getCursorScreenPoint()
      const bounds = petWindow.getBounds()
      const normalizedX = Math.max(-1, Math.min(1, ((cursor.x - bounds.x) / bounds.width) * 2 - 1))
      const normalizedY = Math.max(-1, Math.min(1, ((cursor.y - bounds.y) / bounds.height) * 2 - 1))
      // 脏标记：坐标变化超过阈值才发送 IPC，省掉 ~95% 无意义轮询
      if (Math.abs(normalizedX - _lastMouseX) > MOUSE_MOVE_THRESHOLD ||
          Math.abs(normalizedY - _lastMouseY) > MOUSE_MOVE_THRESHOLD) {
        _lastMouseX = normalizedX
        _lastMouseY = normalizedY
        petWindow.webContents.send('global-mouse-move', { x: normalizedX, y: normalizedY })
      }
    } catch {
      // 静默忽略
    }
  }, 1000) // 1fps：桌面宠物对鼠标跟随延迟不敏感，1s 足够
}

function stopMouseTracking(): void {
  if (mouseTrackInterval) {
    clearInterval(mouseTrackInterval)
    mouseTrackInterval = null
  }
}

export function setPetVisibilityCallback(cb: (visible: boolean) => void): void {
  visibilityCallback = cb
}

export function createPetWindow(): BrowserWindow {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  petWindow = new BrowserWindow({
    width: 640,
    height: 1024,
    x: width - 420,
    y: height - 520,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    resizable: true,
    minWidth: 200,
    minHeight: 200,
    skipTaskbar: true,
    hasShadow: false,
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false, // 允许加载本地 PMX 模型文件
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
    stopMouseTracking()
    if (petWindow && !petWindow.isDestroyed()) {
      petWindow.webContents.send('pet:visibility-change', false)
    }
    visibilityCallback?.(false)
  })
  petWindow.on('show', () => {
    startMouseTracking()
    if (petWindow && !petWindow.isDestroyed()) {
      petWindow.webContents.send('pet:visibility-change', true)
    }
    visibilityCallback?.(true)
  })

  // 窗口关闭处理
  petWindow.on('closed', () => {
    stopMouseTracking()
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
