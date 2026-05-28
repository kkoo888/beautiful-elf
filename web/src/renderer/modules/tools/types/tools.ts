/** 工具管理模块类型定义 */

/** 工具状态 */
export type ToolStatus = 'active' | 'inactive' | 'error'

/** 工具注册信息 */
export interface ToolInfo {
  /** 工具 ID */
  id: string
  /** 工具名称 */
  name: string
  /** 描述 */
  description: string
  /** 所属模块 */
  module: string
  /** 状态 */
  status: ToolStatus
  /** 版本 */
  version: string
  /** 注册时间 */
  registeredAt: string
  /** 最后调用时间 */
  lastCalledAt?: string
}

/** 工具调用统计 */
export interface ToolStats {
  /** 工具 ID */
  toolId: string
  /** 工具名称 */
  toolName: string
  /** 调用次数 */
  callCount: number
  /** 成功次数 */
  successCount: number
  /** 失败次数 */
  failureCount: number
  /** 成功率 */
  successRate: number
  /** 平均耗时（毫秒） */
  avgDurationMs: number
  /** 最近 24h 调用次数 */
  last24hCalls: number
}

/** 工具调用统计汇总 */
export interface ToolStatsSummary {
  /** 总工具数 */
  totalTools: number
  /** 活跃工具数 */
  activeTools: number
  /** 总调用次数 */
  totalCalls: number
  /** 平均成功率 */
  avgSuccessRate: number
}
