/** 性能监控模块类型定义 */

/** 性能指标数据点 */
export interface PerformanceMetric {
  /** CPU 使用率 (%) */
  cpu: number
  /** 内存使用率 (%) */
  memory: number
  /** 磁盘使用率 (%) */
  disk: number
  /** GPU 使用率 (%) - 可选 */
  gpu?: number
  /** 时间戳 (ISO 字符串) */
  timestamp: string
}

/** 告警类型 */
export type AlertType = 'cpu' | 'memory' | 'disk'

/** 性能告警 */
export interface PerformanceAlert {
  /** 告警类型 */
  type: AlertType
  /** 当前值 */
  value: number
  /** 阈值 */
  threshold: number
  /** 告警时间戳 */
  timestamp: string
}

/** 告警阈值配置 */
export interface AlertThresholds {
  cpu: number
  memory: number
  disk: number
}

/** 默认告警阈值 */
export const DEFAULT_THRESHOLDS: AlertThresholds = {
  cpu: 80,
  memory: 85,
  disk: 90,
}
