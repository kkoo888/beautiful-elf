/**
 * API 响应通用类型
 *
 * 后端 FastAPI + Pydantic CamelModel 统一返回 camelCase。
 * 前端全链路 camelCase，无需字段名转换。
 */

/** API 统一响应格式 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
  requestId?: string
}

/** 分页响应格式（与后端 PaginatedResponse 对齐） */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

/** API 错误响应 */
export interface ApiErrorResponse {
  code: number
  message: string
  detail?: string
  requestId?: string
}

/** 分页请求参数 */
export interface PaginationParams {
  page?: number
  pageSize?: number
}

/** 排序参数 */
export interface SortParams {
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}
