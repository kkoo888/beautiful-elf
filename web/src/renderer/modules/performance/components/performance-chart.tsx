/**
 * 性能趋势图组件
 * 使用自定义 CSS 条形图展示历史趋势，不引入额外图表库
 */

import React, { useMemo } from 'react'
import { Tooltip } from 'antd'
import type { PerformanceMetric } from '../types/performance'
import styles from './performance-panel.module.css'

export interface PerformanceChartProps {
  /** 历史数据 */
  data: PerformanceMetric[]
  /** 指标字段 */
  field: 'cpu' | 'memory' | 'disk'
  /** 图表标题 */
  title: string
  /** 告警阈值 */
  threshold: number
}

export const PerformanceChart: React.FC<PerformanceChartProps> = ({
  data,
  field,
  title,
  threshold,
}) => {
  // 提取最近 20 个数据点
  const chartData = useMemo(() => {
    return data.slice(-20).map((d) => ({
      value: d[field] as number,
      time: new Date(d.timestamp).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }),
      fullTime: new Date(d.timestamp).toLocaleString('zh-CN'),
    }))
  }, [data, field])

  const maxValue = useMemo(() => {
    return Math.max(...chartData.map((d) => d.value), threshold) * 1.1
  }, [chartData, threshold])

  return (
    <div className={styles.chartContainer}>
      <div className={styles.chartTitle}>{title}</div>
      <div className={styles.chartBody}>
        {chartData.map((point, index) => {
          const heightPercent = (point.value / maxValue) * 100
          const isOver = point.value >= threshold
          return (
            <div key={index} className={styles.chartBarWrapper}>
              <div className={styles.chartBarTrack}>
                <div
                  className={`${styles.chartBar} ${isOver ? styles.chartBarDanger : ''}`}
                  style={{ height: `${heightPercent}%` }}
                />
              </div>
              {index % 4 === 0 && (
                <Tooltip title={point.fullTime}>
                  <span className={styles.chartLabel}>
                    {point.time.slice(0, 5)}
                  </span>
                </Tooltip>
              )}
            </div>
          )
        })}
        {/* 阈值线 — 在 chartBody 内定位（条形区 116px + 底部 label 24px） */}
        {chartData.length > 0 && (
          <div
            className={styles.chartThresholdLine}
            style={{ bottom: `calc(24px + ${(threshold / maxValue) * 116}px)` }}
          >
            <span className={styles.chartThresholdLabel}>阈值 {threshold}%</span>
          </div>
        )}
      </div>
    </div>
  )
}
