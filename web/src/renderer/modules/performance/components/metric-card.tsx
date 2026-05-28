/**
 * 指标卡片组件
 * 使用 Ant Design Progress 展示百分比，超过阈值变红色
 */

import React from 'react'
import { Progress, Tooltip } from 'antd'
import styles from './performance-panel.module.css'

export interface MetricCardProps {
  /** 指标标题 */
  title: string
  /** 当前值 */
  value: number
  /** 单位 */
  unit?: string
  /** 告警阈值 */
  threshold: number
  /** 图标 */
  icon: React.ReactNode
}

/** 根据值和阈值决定颜色 */
function getProgressColor(value: number, threshold: number): string {
  if (value >= threshold) return '#ff4d4f'
  if (value >= threshold * 0.8) return '#faad14'
  return '#52c41a'
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit = '%',
  threshold,
  icon,
}) => {
  const color = getProgressColor(value, threshold)
  const isWarning = value >= threshold
  const displayValue = value.toFixed(1)

  return (
    <div className={`${styles.metricCard} ${isWarning ? styles.metricCardWarning : ''}`}>
      <div className={styles.metricHeader}>
        <span className={styles.metricIcon}>{icon}</span>
        <span className={styles.metricTitle}>{title}</span>
      </div>
      <div className={styles.metricBody}>
        <Progress
          type="dashboard"
          percent={Math.min(value, 100)}
          strokeColor={color}
          trailColor="var(--ant-color-fill-secondary)"
          size={100}
          format={() => (
            <span className={styles.metricValue} style={{ color }}>
              {displayValue}
              <span className={styles.metricUnit}>{unit}</span>
            </span>
          )}
        />
      </div>
      <Tooltip title={`告警阈值: ${threshold}${unit}`}>
        <div className={styles.metricFooter}>
          阈值: {threshold}{unit}
        </div>
      </Tooltip>
    </div>
  )
}
