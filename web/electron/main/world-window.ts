import { BrowserWindow, screen, ipcMain } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'

let worldWindow: BrowserWindow | null = null
let mouseTrackInterval: ReturnType<typeof setInterval> | null = null

// 鼠标追踪脏标记
let _lastMouseX = 0
let _lastMouseY = 0
const MOUSE_MOVE_THRESHOLD = 0.002

function startMouseTracking(): void {
  if (mouseTrackInterval) return
  _lastMouseX = NaN
  _lastMouseY = NaN
  mouseTrackInterval = setInterval(() => {
    if (!worldWindow || worldWindow.isDestroyed()) {
      stopMouseTracking()
      return
    }
    try {
      const cursor = screen.getCursorScreenPoint()
      const bounds = worldWindow.getBounds()
      const normalizedX = Math.max(-1, Math.min(1, ((cursor.x - bounds.x) / bounds.width) * 2 - 1))
      const normalizedY = Math.max(-1, Math.min(1, ((cursor.y - bounds.y) / bounds.height) * 2 - 1))
      if (
        Math.abs(normalizedX - _lastMouseX) > MOUSE_MOVE_THRESHOLD ||
        Math.abs(normalizedY - _lastMouseY) > MOUSE_MOVE_THRESHOLD
      ) {
        _lastMouseX = normalizedX
        _lastMouseY = normalizedY
        worldWindow.webContents.send('global-mouse-move', { x: normalizedX, y: normalizedY })
      }
    } catch {
      // 静默忽略
    }
  }, 1000)
}

function stopMouseTracking(): void {
  if (mouseTrackInterval) {
    clearInterval(mouseTrackInterval)
    mouseTrackInterval = null
  }
}

export function createWorldWindow(): BrowserWindow {
  if (worldWindow && !worldWindow.isDestroyed()) {
    worldWindow.show()
    return worldWindow
  }

  worldWindow = new BrowserWindow({
    width: 1024,
    height: 860,
    show: false,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    hasShadow: false,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,
    },
  })

  // 加载页面
  if (is.dev && process.env.ELECTRON_RENDERER_URL) {
    worldWindow.loadURL(`${process.env.ELECTRON_RENDERER_URL}/world-window.html`)
  } else {
    worldWindow.loadFile(join(__dirname, '../renderer/world-window.html'))
  }

  // 窗口显示/隐藏时通知
  worldWindow.on('show', () => {
    startMouseTracking()
    worldWindow?.webContents.send('world:visibility-change', true)
    ipcMain.emit('world:visibility-change', null, true)
  })

  worldWindow.on('hide', () => {
    stopMouseTracking()
    worldWindow?.webContents.send('world:visibility-change', false)
    ipcMain.emit('world:visibility-change', null, false)
  })

  worldWindow.on('closed', () => {
    stopMouseTracking()
    worldWindow = null
  })

  return worldWindow
}

export function getWorldWindow(): BrowserWindow | null {
  return worldWindow
}

export function showWorldWindow(): void {
  if (worldWindow && !worldWindow.isDestroyed()) {
    worldWindow.show()
  }
}

export function hideWorldWindow(): void {
  if (worldWindow && !worldWindow.isDestroyed()) {
    worldWindow.hide()
  }
}

export function isWorldWindowVisible(): boolean {
  return worldWindow !== null && !worldWindow.isDestroyed() && worldWindow.isVisible()
}
