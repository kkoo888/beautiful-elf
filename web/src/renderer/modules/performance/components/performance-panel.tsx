/**
 * 性能监控主面板
 * 展示 CPU / 内存 / 磁盘三个 MetricCard + 趋势图 + 告警
 */

import React from 'react'
import { Alert, Row, Col, Spin, Card, Statistic, Tag, Space, Tooltip } from 'antd'
import {
  DesktopOutlined,
  DatabaseOutlined,
  HddOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons'
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

/** 性能监控面板 */
export const PerformancePanel: React.FC = () => {
  const { latest, metrics, isLoading, isFetching, alerts, hasAlerts } = usePerformance()

  // 首次加载且无数据时才显示全屏 loading
  if (isLoading && metrics.length === 0) {
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
      <PageHeader
        title="📊 性能监控"
        description={
          <Space>
            <span>CPU / 内存 / 磁盘实时监控（每 5 秒刷新）</span>
            {isFetching && <ReloadOutlined spin style={{ color: 'var(--ant-color-primary)' }} />}
          </Space>
        }
      />

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
          <Card hoverable className={styles.metricCard}>
            <Space orientation="vertical" align="center" style={{ width: '100%' }}>
              <Space>
                <DesktopOutlined style={{ fontSize: 20, color: 'var(--ant-color-primary)' }} />
                <span style={{ fontWeight: 600 }}>CPU 使用率</span>
                <HealthTag value={latest?.cpu ?? 0} threshold={DEFAULT_THRESHOLDS.cpu} />
              </Space>
              <MetricCard
                title=""
                value={latest?.cpu ?? 0}
                threshold={DEFAULT_THRESHOLDS.cpu}
                icon={<span />}
              />
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card hoverable className={styles.metricCard}>
            <Space orientation="vertical" align="center" style={{ width: '100%' }}>
              <Space>
                <DatabaseOutlined style={{ fontSize: 20, color: 'var(--ant-color-primary)' }} />
                <span style={{ fontWeight: 600 }}>内存使用率</span>
                <HealthTag value={latest?.memory ?? 0} threshold={DEFAULT_THRESHOLDS.memory} />
              </Space>
              <MetricCard
                title=""
                value={latest?.memory ?? 0}
                threshold={DEFAULT_THRESHOLDS.memory}
                icon={<span />}
              />
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card hoverable className={styles.metricCard}>
            <Space orientation="vertical" align="center" style={{ width: '100%' }}>
              <Space>
                <HddOutlined style={{ fontSize: 20, color: 'var(--ant-color-primary)' }} />
                <span style={{ fontWeight: 600 }}>磁盘使用率</span>
                <HealthTag value={latest?.disk ?? 0} threshold={DEFAULT_THRESHOLDS.disk} />
              </Space>
              <MetricCard
                title=""
                value={latest?.disk ?? 0}
                threshold={DEFAULT_THRESHOLDS.disk}
                icon={<span />}
              />
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 趋势图 */}
      <Card title="📈 趋势图" className={styles.chartCard}>
        <Row gutter={16}>
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
      </Card>
    </div>
  )
}
