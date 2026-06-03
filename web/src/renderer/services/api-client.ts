/**
 * HTTP 客户端
 *
 * 后端 FastAPI + Pydantic CamelModel 统一返回 camelCase。
 * 提供统一的响应提取函数，消除 `as any` 类型逃逸。
 *
 * @see http-client skill — interceptors, error handling, security patterns
 * @see fastapi skill — Pydantic CamelModel alias_generator=to_camel, populate_by_name=True
 */

import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'
import { handleApiError } from './api-error'
import type { ApiResponse, PaginatedResponse } from '@/types'

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
// 注入 trace_id，便于全链路追踪。不做 camelToSnake 转换。
// 后端 CamelModel 的 populate_by_name=True 已支持 camelCase 请求体。

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

// ── 响应提取工具 ───────────────────────────────────────────
// 后端响应格式：
//   成功: { code: "SUCCESS", message: "...", data: T }
//   分页: { code: "SUCCESS", message: "...", data: T[], meta: { total, page, page_size } }
//   失败: { code: "ERROR_CODE", message: "...", data: null, request_id: "..." }

/**
 * 从 ApiResponse<T> 中提取 data 字段
 *
 * @example
 * const user = extractData(await apiClient.get<User>('/users/1'))
 */
function extractData<T>(resp: AxiosResponse<ApiResponse<T>>): T {
  return resp.data.data
}

/**
 * 从分页 ApiResponse<T[]> 中提取 items + total
 * 后端 ok_page() 返回 { data, meta: { total, page, page_size } }
 *
 * @example
 * const { items, total } = extractPaginated(await apiClient.get<User[]>('/users'))
 */
function extractPaginated<T>(resp: AxiosResponse<ApiResponse<T[]>>): PaginatedResponse<T> {
  const body = resp.data as any
  const meta = body.meta ?? {}
  return {
    items: body.data ?? [],
    total: meta.total ?? 0,
    page: meta.page ?? 1,
    pageSize: meta.pageSize ?? (body.data?.length ?? 0),
  }
}

export { apiClient, extractData, extractPaginated }
