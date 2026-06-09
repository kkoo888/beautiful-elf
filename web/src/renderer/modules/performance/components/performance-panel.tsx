/**
 * 性能监控主面板
 * 展示 CPU / 内存 / 磁盘三个 MetricCard + 趋势图 + 告警
 */

import React from 'react'
import { Alert, Spin, Card, Space } from 'antd'
import {
  DesktopOutlined,
  DatabaseOutlined,
  HddOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { usePerformance } from '../hooks/use-performance'
import { MetricCard } from './metric-card'
import { PerformanceChart } from './performance-chart'
import { DEFAULT_THRESHOLDS } from '../types/performance'
import styles from './performance-panel.module.css'

/** 告警类型对应中文标签 */
const ALERT_LABELS: Record<string, string> = {
  cpu: 'CPU',
  memory: '内存',
  disk: '磁盘',
}

/** 性能监控面板 */
export const PerformancePanel: React.FC = () => {
  const { latest, metrics, isLoading, isFetching, alerts, hasAlerts } = usePerformance()

  // 首次加载且无数据时显示全屏 loading
  if (isLoading && metrics.length === 0) {
    return (
      <div className={styles.panel}>
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <Spin size="large" tip="加载性能数据中..." />
        </div>
      </div>
    )
  }

  return (
    <div className={styles.panel}>
      {/* 顶部状态栏 */}
      <div className={styles.statusBar}>
        <span className={styles.statusLabel}>
          每 5 秒自动刷新
        </span>
        {isFetching && <ReloadOutlined spin style={{ color: 'var(--ant-color-primary)' }} />}
      </div>

      {/* 告警区域 */}
      {hasAlerts && (
        <div className={styles.alertsSection}>
          {alerts.map((alert) => (
            <Alert
              key={alert.type}
              type="warning"
              showIcon
              banner
              message={`${ALERT_LABELS[alert.type]} 使用率过高: ${alert.value.toFixed(1)}%（阈值 ${alert.threshold}%）`}
            />
          ))}
        </div>
      )}

      {/* 指标卡片 */}
      <div className={styles.metricGrid}>
        <MetricCard
          title="CPU 使用率"
          value={latest?.cpu ?? 0}
          threshold={DEFAULT_THRESHOLDS.cpu}
          icon={<DesktopOutlined style={{ fontSize: 20, color: 'var(--ant-color-primary)' }} />}
        />
        <MetricCard
          title="内存使用率"
          value={latest?.memory ?? 0}
          threshold={DEFAULT_THRESHOLDS.memory}
          icon={<DatabaseOutlined style={{ fontSize: 20, color: 'var(--ant-color-primary)' }} />}
        />
        <MetricCard
          title="磁盘使用率"
          value={latest?.disk ?? 0}
          threshold={DEFAULT_THRESHOLDS.disk}
          icon={<HddOutlined style={{ fontSize: 20, color: 'var(--ant-color-primary)' }} />}
        />
      </div>

      {/* 趋势图 */}
      <Card title="📈 趋势图" className={styles.chartCard}>
        <div className={styles.chartGrid}>
          <PerformanceChart
            data={metrics}
            field="cpu"
            title="CPU 趋势"
            threshold={DEFAULT_THRESHOLDS.cpu}
          />
          <PerformanceChart
            data={metrics}
            field="memory"
            title="内存趋势"
            threshold={DEFAULT_THRESHOLDS.memory}
          />
          <PerformanceChart
            data={metrics}
            field="disk"
            title="磁盘趋势"
            threshold={DEFAULT_THRESHOLDS.disk}
          />
        </div>
      </Card>
    </div>
  )
}
