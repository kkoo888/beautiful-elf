// 应用常量
export const APP_NAME = 'Beautiful-Elf'
export const APP_VERSION = '0.1.0'

// API 配置
export const API_BASE_URL = 'http://localhost:8000'
export const API_VERSION = 'v1'
export const API_PREFIX = `/api/${API_VERSION}`

// WebSocket 配置
export const WS_URL = 'ws://localhost:8000/api/v1/ws'
export const WS_HEARTBEAT_INTERVAL = 30000 // 30秒
export const WS_RECONNECT_INITIAL = 1000 // 初始重连间隔 1秒
export const WS_RECONNECT_MAX = 30000 // 最大重连间隔 30秒

// 存储 Key
export const STORAGE_KEYS = {
  THEME: 'beautiful-elf:theme',
  SETTINGS: 'beautiful-elf:settings',
  CONVERSATIONS: 'beautiful-elf:conversations',
} as const

// 主题
export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  HIGH_CONTRAST: 'high-contrast',
} as const

// 事件类型
export const IPC_CHANNELS = {
  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_CLOSE: 'window:close',
  WINDOW_IS_MAXIMIZED: 'window:isMaximized',
  APP_GET_VERSION: 'app:getVersion',
} as const
