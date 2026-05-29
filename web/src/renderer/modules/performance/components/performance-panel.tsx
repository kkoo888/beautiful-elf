/**
 * 性能监控主面板
 * 展示 CPU / 内存 / 磁盘三个 MetricCard + 趋势图 + 告警
 */

import React from 'react'
import { Alert, Row, Col, Spin } from 'antd'
import { DesktopOutlined, DatabaseOutlined, HddOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
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
  const { latest, metrics, isLoading, alerts, hasAlerts } = usePerformance()

  if (isLoading) {
    return (
      <div className={styles.panel}>
        <PageHeader title="📊 性能监控" description="CPU / 内存 / 磁盘实时监控" />
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" tip="加载性能数据中..." />
        </div>
      </div>
    )
  }

  return (
    <div className={styles.panel}>
      <PageHeader title="📊 性能监控" description="CPU / 内存 / 磁盘实时监控（每 5 秒刷新）" />

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
      <Row gutter={16} className={styles.metricRow}>
        <Col span={8}>
          <MetricCard
            title="CPU 使用率"
            value={latest?.cpu ?? 0}
            threshold={DEFAULT_THRESHOLDS.cpu}
            icon={<DesktopOutlined />}
          />
        </Col>
        <Col span={8}>
          <MetricCard
            title="内存使用率"
            value={latest?.memory ?? 0}
            threshold={DEFAULT_THRESHOLDS.memory}
            icon={<DatabaseOutlined />}
          />
        </Col>
        <Col span={8}>
          <MetricCard
            title="磁盘使用率"
            value={latest?.disk ?? 0}
            threshold={DEFAULT_THRESHOLDS.disk}
            icon={<HddOutlined />}
          />
        </Col>
      </Row>

      {/* 趋势图 */}
      <Row gutter={16} className={styles.chartSection}>
        <Col span={8}>
          <PerformanceChart
            data={metrics}
            field="cpu"
            title="CPU 趋势"
            threshold={DEFAULT_THRESHOLDS.cpu}
          />
        </Col>
        <Col span={8}>
          <PerformanceChart
            data={metrics}
            field="memory"
            title="内存趋势"
            threshold={DEFAULT_THRESHOLDS.memory}
          />
        </Col>
        <Col span={8}>
          <PerformanceChart
            data={metrics}
            field="disk"
            title="磁盘趋势"
            threshold={DEFAULT_THRESHOLDS.disk}
          />
        </Col>
      </Row>
    </div>
  )
}
