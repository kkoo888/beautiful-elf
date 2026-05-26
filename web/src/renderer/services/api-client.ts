import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'
import { camelToSnake, snakeToCamel } from '@/utils'
import type { ApiResponse } from '@/types'

const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：camelCase → snake_case
apiClient.interceptors.request.use(
  (config) => {
    if (config.data && typeof config.data === 'object') {
      config.data = camelToSnake(config.data)
    }

    // 生成 trace_id
    const traceId = crypto.randomUUID()
    config.headers['X-Trace-Id'] = traceId

    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：snake_case → camelCase
apiClient.interceptors.response.use(
  (response: AxiosResponse<ApiResponse<unknown>>) => {
    if (response.data && typeof response.data === 'object') {
      const data = response.data as Record<string, unknown>
      if (data.data && typeof data.data === 'object') {
        data.data = snakeToCamel(data.data as Record<string, unknown>)
      }
    }
    return response
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '网络错误'
    console.error('[API Error]', message)
    return Promise.reject(error)
  }
)

export { apiClient }
