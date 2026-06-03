/**
 * HTTP 客户端
 *
 * 后端 CamelModel 已统一返回 camelCase，前端全链路 camelCase。
 * 请求/响应拦截器仅保留 trace_id 注入和错误处理，不做字段名转换。
 *
 * @see http-client skill — interceptors, error handling, security patterns
 */

import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'
import { handleApiError } from './api-error'
import type { ApiResponse } from '@/types'

/**
 * Axios 实例
 * baseURL + timeout + JSON headers
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── 请求拦截器 ─────────────────────────────────────────────
// 注入 trace_id，便于全链路追踪。不做 camelToSnake 转换（后端已支持 camelCase）。

apiClient.interceptors.request.use(
  (config) => {
    config.headers['X-Trace-Id'] = crypto.randomUUID()
    return config
  },
  (error) => Promise.reject(error)
)

// ── 响应拦截器 ─────────────────────────────────────────────
// 统一错误处理。不做 snakeToCamel 转换（后端 CamelModel 已返回 camelCase）。

apiClient.interceptors.response.use(
  (response: AxiosResponse<ApiResponse<unknown>>) => response,
  (error) => {
    const message = handleApiError(error)
    return Promise.reject(new Error(message))
  }
)

export { apiClient }
