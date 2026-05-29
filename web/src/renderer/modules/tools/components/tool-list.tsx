/** 工具注册表组件（Table） */

import { Table, Tag, Typography, Space } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { ToolInfo, ToolStats } from '../types/tools'
import { EmptyState } from '@/components/empty-state'
import styles from './tools-panel.module.css'

const { Text } = Typography

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  active: { label: '活跃', color: 'success' },
  inactive: { label: '停用', color: 'default' },
  error: { label: '异常', color: 'error' },
}

interface ToolListProps {
  tools: Array<ToolInfo & Partial<ToolStats>>
  loading?: boolean
}

export function ToolList({ tools, loading }: ToolListProps) {
  const columns: ColumnsType<ToolInfo & Partial<ToolStats>> = [
    {
      title: '工具名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <Text code strong>
            {name}
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.description}
          </Text>
        </Space>
      ),
    },
    {
      title: '所属模块',
      dataIndex: 'module',
      key: 'module',
      width: 120,
      render: (module: string) => <Tag>{module}</Tag>,
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 80,
      render: (v: string) => <Text type="secondary">{v}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => {
        const { label, color } = STATUS_MAP[status] ?? STATUS_MAP.inactive
        return <Tag color={color}>{label}</Tag>
      },
    },
    {
      title: '调用次数',
      dataIndex: 'callCount',
      key: 'callCount',
      width: 100,
      align: 'right',
      render: (count?: number) => count?.toLocaleString() ?? '-',
    },
    {
      title: '成功率',
      key: 'successRate',
      width: 140,
      render: (_: unknown, record) => {
        const rate = record.successRate
        if (rate === undefined) return '-'
        const color =
          rate >= 95
            ? 'var(--ant-color-success)'
            : rate >= 85
              ? 'var(--ant-color-warning)'
              : 'var(--ant-color-error)'
        return (
          <div className={styles.successRateBar}>
            <div className={styles.rateBar}>
              <div
                className={styles.rateBarFill}
                style={{ width: `${rate}%`, background: color }}
              />
            </div>
            <span className={styles.rateText} style={{ color }}>
              {rate}%
            </span>
          </div>
        )
      },
    },
    {
      title: '平均耗时',
      dataIndex: 'avgDurationMs',
      key: 'avgDuration',
      width: 100,
      align: 'right',
      render: (ms?: number) => {
        if (ms === undefined) return '-'
        return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
      },
    },
    {
      title: '最近 24h',
      dataIndex: 'last24hCalls',
      key: 'last24h',
      width: 90,
      align: 'right',
      render: (count?: number) => count?.toLocaleString() ?? '-',
    },
  ]

  if (tools.length === 0 && !loading) {
    return <EmptyState icon="🔌" description="暂无注册工具" />
  }

  return (
    <Table
      columns={columns}
      dataSource={tools}
      rowKey="id"
      loading={loading}
      pagination={false}
      size="middle"
    />
  )
}
