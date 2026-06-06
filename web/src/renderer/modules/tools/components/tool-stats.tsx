/** 调用统计组件 */

import { Spin, Typography } from 'antd'
import type { ToolStatsSummary } from '../types/tools'
import { EmptyState } from '@/components/empty-state'
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

  if (!summary) {
    return <EmptyState icon="📊" description="暂无统计数据" />
  }

  const stats = [
    { label: '工具总数', value: summary.totalTools, unit: '个' },
    { label: '活跃工具', value: summary.activeTools, unit: '个' },
    { label: '总调用次数', value: summary.totalCalls.toLocaleString(), unit: '次' },
    { label: '平均成功率', value: summary.avgSuccessRate, unit: '%' },
  ]

  return (
    <div className={styles.statsRow}>
      {stats.map((stat) => (
        <div key={stat.label} className={styles.statCard}>
          <div className={styles.statLabel}>{stat.label}</div>
          <div className={styles.statValue}>
            {stat.value}
            <span className={styles.statUnit}>{stat.unit}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
