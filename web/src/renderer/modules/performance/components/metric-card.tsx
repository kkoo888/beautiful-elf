/**
 * 指标卡片组件
 * 自包含：图标 + 标题 + 健康标签 + 仪表盘进度 + 阈值提示
 */

import React from 'react'
import { Progress, Tag, Tooltip } from 'antd'
import { CheckCircleOutlined, WarningOutlined } from '@ant-design/icons'
import styles from './performance-panel.module.css'

export interface MetricCardProps {
  /** 指标标题 */
  title: string
  /** 当前值 (0-100) */
  value: number
  /** 单位 */
  unit?: string
  /** 告警阈值 */
  threshold: number
  /** 图标 */
  icon: React.ReactNode
}

/** 根据值和阈值决定进度条颜色 */
function getProgressColor(value: number, threshold: number): string {
  if (value >= threshold) return '#ff4d4f'
  if (value >= threshold * 0.8) return '#faad14'
  return '#52c41a'
}

/** 健康状态标签 */
function HealthTag({ value, threshold }: { value: number; threshold: number }) {
  if (value >= threshold) {
    return <Tag color="error" icon={<WarningOutlined />}>危险</Tag>
  }
  if (value >= threshold * 0.8) {
    return <Tag color="warning" icon={<WarningOutlined />}>警告</Tag>
  }
  return <Tag color="success" icon={<CheckCircleOutlined />}>正常</Tag>
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit = '%',
  threshold,
  icon,
}) => {
  const color = getProgressColor(value, threshold)
  const isDanger = value >= threshold

  return (
    <div className={`${styles.metricCard} ${isDanger ? styles.metricCardDanger : ''}`}>
      <div className={styles.metricHeader}>
        <span className={styles.metricIcon}>{icon}</span>
        <span className={styles.metricTitle}>{title}</span>
        <HealthTag value={value} threshold={threshold} />
      </div>
      <div className={styles.metricBody}>
        <Progress
          type="dashboard"
          percent={Math.min(value, 100)}
          strokeColor={color}
          railColor="var(--ant-color-fill-secondary)"
          size={100}
          format={() => (
            <span className={styles.metricValue} style={{ color }}>
              {value.toFixed(1)}
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
