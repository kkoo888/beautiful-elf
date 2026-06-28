/** 工具管理模块类型定义 */

/** 工具注册信息 */
export interface ToolInfo {
  /** 工具 ID */
  id: number
  /** 工具名称 */
  name: string
  /** 显示名称 */
  displayName: string
  /** 描述 */
  description: string
  /** 功能类别（增/删/改/查/计算/其他） */
  module: string
  /** 工具分组: search/file/code/git/data/memory/media/comm/agent/doc/general */
  category: string
  /** JSON Schema */
  jsonSchema: Record<string, unknown>
  /** 风险等级 */
  riskLevel: string
  /** 是否启用 */
  isEnabled: number
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

/** 工具统计汇总 */
export interface ToolStatsSummary {
  /** 工具总数 */
  totalTools: number
  /** 活跃工具数 */
  activeTools: number
  /** 总调用次数 */
  totalCalls: number
  /** 平均成功率（百分比） */
  avgSuccessRate: number
}

/** 工具状态 */
export type ToolStatus = 'active' | 'inactive' | 'error'

/** 工具列表查询参数 */
export interface ToolQueryParams {
  page?: number
  pageSize?: number
  isEnabled?: number
}

/** 工具创建参数 */
export interface CreateToolInput {
  name: string
  displayName: string
  description: string
  module: string
  category?: string
  jsonSchema: Record<string, unknown>
  riskLevel: string
}

/** 工具更新参数 */
export interface UpdateToolInput {
  displayName?: string
  description?: string
  module?: string
  category?: string
  jsonSchema?: Record<string, unknown>
  riskLevel?: string
}

/** 分页结果 */
export interface PaginatedResult<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
}
