/**
 * API 响应通用类型
 */

/** API 统一响应格式 */
export interface ApiResponse<T> {
  code: string
  message: string
  data: T
  request_id: string
}

/** 分页响应格式 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** API 错误响应 */
export interface ApiErrorResponse {
  code: string
  message: string
  detail?: string
  request_id: string
}

/** 分页请求参数 */
export interface PaginationParams {
  page?: number
  page_size?: number
}

/** 排序参数 */
export interface SortParams {
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}
