// ============================================
// 应用常量 — 优先读取环境变量，回退到默认值
// ============================================

// ---------- 应用信息 ----------
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Beautiful-Elf'
export const APP_VERSION = import.meta.env.VITE_APP_VERSION || '0.1.0'

// ---------- API 配置 ----------
const API_HOST = import.meta.env.VITE_API_HOST || 'localhost'
const API_PORT = import.meta.env.VITE_API_PORT || '8000'
export const API_BASE_URL = `http://${API_HOST}:${API_PORT}`
export const API_VERSION = 'v1'
export const API_PREFIX = import.meta.env.VITE_API_PREFIX || `/api/${API_VERSION}`

// ---------- WebSocket 配置 ----------
const WS_HOST = import.meta.env.VITE_WS_HOST || 'localhost'
const WS_PORT = import.meta.env.VITE_WS_PORT || '8000'
const WS_PATH = import.meta.env.VITE_WS_PATH || `/api/${API_VERSION}/ws`
export const WS_URL = `ws://${WS_HOST}:${WS_PORT}${WS_PATH}`
export const WS_HEARTBEAT_INTERVAL = 30000 // 30秒
export const WS_RECONNECT_INITIAL = 1000 // 初始重连间隔 1秒
export const WS_RECONNECT_MAX = 30000 // 最大重连间隔 30秒

// ---------- 功能开关 ----------
export const ENABLE_MOCK = import.meta.env.VITE_ENABLE_MOCK === 'true'
export const ENABLE_DEVTOOLS = import.meta.env.VITE_ENABLE_DEVTOOLS === 'true'
export const ENABLE_SENTRY = import.meta.env.VITE_ENABLE_SENTRY === 'true'

// ---------- 存储 Key ----------
export const STORAGE_KEYS = {
  THEME: 'beautiful-elf:theme',
  SETTINGS: 'beautiful-elf:settings',
  CONVERSATIONS: 'beautiful-elf:conversations',
} as const

// ---------- 主题 ----------
export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  HIGH_CONTRAST: 'high-contrast',
} as const

// ---------- 事件类型 ----------
export const IPC_CHANNELS = {
  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_CLOSE: 'window:close',
  WINDOW_IS_MAXIMIZED: 'window:isMaximized',
  APP_GET_VERSION: 'app:getVersion',
} as const
