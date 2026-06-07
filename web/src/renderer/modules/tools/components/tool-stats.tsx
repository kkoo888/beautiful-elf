/** 调用统计汇总卡片 */

import { Spin, Typography } from 'antd'
import type { ToolStatsSummary } from '../types/tools'
import styles from './tools-panel.module.css'

const { Text } = Typography

interface ToolStatsProps {
  summary: ToolStatsSummary | undefined
  loading?: boolean
}

export function ToolStats({ summary, loading }: ToolStatsProps) {
  if (loading) {
    return <Spin style={{ display: 'block', textAlign: 'center', padding: 24 }} />
  }

  if (!summary) return null

  const stats = [
    { label: '工具总数', value: summary.totalTools, unit: '个', color: 'var(--ant-color-primary)' },
    { label: '已启用', value: summary.activeTools, unit: '个', color: 'var(--ant-color-success)' },
  ]

  return (
    <div className={styles.statsRow}>
      {stats.map((stat) => (
        <div key={stat.label} className={styles.statCard}>
          <div className={styles.statLabel}>{stat.label}</div>
          <div className={styles.statValue} style={{ color: stat.color }}>
            {stat.value}
            <span className={styles.statUnit}>{stat.unit}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
