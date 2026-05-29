/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 应用名称 */
  readonly VITE_APP_NAME: string
  /** 应用版本 */
  readonly VITE_APP_VERSION: string
  /** API 服务器主机 */
  readonly VITE_API_HOST: string
  /** API 服务器端口 */
  readonly VITE_API_PORT: string
  /** API 路径前缀 */
  readonly VITE_API_PREFIX: string
  /** WebSocket 主机 */
  readonly VITE_WS_HOST: string
  /** WebSocket 端口 */
  readonly VITE_WS_PORT: string
  /** WebSocket 路径 */
  readonly VITE_WS_PATH: string
  /** 是否启用 Mock */
  readonly VITE_ENABLE_MOCK: string
  /** 是否启用 DevTools */
  readonly VITE_ENABLE_DEVTOOLS: string
  /** 是否启用 Sentry */
  readonly VITE_ENABLE_SENTRY: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
