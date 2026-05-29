/** 工具管理模块类型定义 */

/** 工具注册信息 */
export interface ToolInfo {
  /** 工具 ID */
  id: string
  /** 工具名称 */
  name: string
  /** 显示名称 */
  displayName: string
  /** 描述 */
  description: string
  /** 所属模块 */
  module: string
  /** JSON Schema */
  jsonSchema: Record<string, unknown>
  /** 是否启用 */
  enabled: boolean
  /** 创建时间 */
  createdAt: string
  /** 更新时间 */
  updatedAt: string
}

/** 工具调用统计 */
export interface ToolStats {
  /** 调用次数 */
  callCount: number
  /** 成功次数 */
  successCount: number
  /** 失败次数 */
  failCount: number
  /** 平均耗时（毫秒） */
  avgDurationMs: number
  /** 最后调用时间 */
  lastCalledAt: string | null
}

/** 工具列表查询参数 */
export interface ToolQueryParams {
  page?: number
  pageSize?: number
  enabled?: number
}

/** 工具创建参数 */
export interface CreateToolInput {
  name: string
  displayName: string
  description: string
  module: string
  jsonSchema: Record<string, unknown>
}

/** 工具更新参数 */
export interface UpdateToolInput {
  displayName?: string
  description?: string
  module?: string
  jsonSchema?: Record<string, unknown>
}

/** 分页结果 */
export interface PaginatedResult<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
}
