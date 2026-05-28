import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'
import { camelToSnake, snakeToCamel } from '@/utils'
import { handleApiError } from './api-error'
import type { ApiResponse } from '@/types'

/**
 * Axios 实例
 * 含请求/响应拦截器、camelCase↔snake_case 转换、trace_id 注入
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：camelCase → snake_case + trace_id 注入
apiClient.interceptors.request.use(
  (config) => {
    // 字段名转换
    if (config.data && typeof config.data === 'object') {
      config.data = camelToSnake(config.data)
    }

    // 生成 trace_id 并注入请求头
    const traceId = crypto.randomUUID()
    config.headers['X-Trace-Id'] = traceId

    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：snake_case → camelCase + 错误处理
apiClient.interceptors.response.use(
  (response: AxiosResponse<ApiResponse<unknown>>) => {
    // 字段名转换
    if (response.data && typeof response.data === 'object') {
      const data = response.data as Record<string, unknown>
      if (data.data && typeof data.data === 'object') {
        data.data = snakeToCamel(data.data as Record<string, unknown>)
      }
    }
    return response
  },
  (error) => {
    // 统一错误处理
    const message = handleApiError(error)
    return Promise.reject(new Error(message))
  }
)

export { apiClient }
