/** 子代理运行列表组件（Table） */

import { Table, Tag, Space, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { SubagentRun, SubagentStatus } from '../types/subagent'
import { SubagentStop } from './subagent-stop'
import { EmptyState } from '@/components/empty-state'

const { Text } = Typography

const STATUS_MAP: Record<SubagentStatus, { label: string; color: string }> = {
  idle: { label: '空闲', color: 'default' },
  running: { label: '运行中', color: 'processing' },
  completed: { label: '已完成', color: 'success' },
  failed: { label: '失败', color: 'error' },
  terminated: { label: '已终止', color: 'warning' },
}

function formatElapsed(ms: number): string {
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (minutes < 60) return `${minutes}m ${secs}s`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h ${mins}m`
}

const PRIORITY_MAP: Record<string, { label: string; color: string }> = {
  high: { label: '高', color: 'red' },
  normal: { label: '中', color: 'blue' },
  low: { label: '低', color: 'default' },
}

interface SubagentListProps {
  runs: SubagentRun[]
  loading?: boolean
  onStop: (id: string) => void
  onSelect: (id: string) => void
  selectedId: string | null
}

export function SubagentList({ runs, loading, onStop, onSelect, selectedId }: SubagentListProps) {
  const columns: ColumnsType<SubagentRun> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 90,
      render: (id: string) => (
        <Text code style={{ fontSize: 12 }}>
          {id}
        </Text>
      ),
    },
    {
      title: '任务名',
      dataIndex: 'taskName',
      key: 'taskName',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: SubagentStatus) => {
        const { label, color } = STATUS_MAP[status]
        return <Tag color={color}>{label}</Tag>
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 70,
      render: (priority: string) => {
        const { label, color } = PRIORITY_MAP[priority] ?? PRIORITY_MAP.normal
        return <Tag color={color}>{label}</Tag>
      },
    },
    {
      title: '已运行',
      dataIndex: 'elapsedMs',
      key: 'elapsed',
      width: 100,
      render: (ms: number) => <Text type="secondary">{formatElapsed(ms)}</Text>,
    },
    {
      title: '当前步骤',
      key: 'currentStep',
      width: 140,
      render: (_: unknown, record: SubagentRun) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {record.currentStep ??
            (record.status === 'completed'
              ? '已完成'
              : record.status === 'failed'
                ? '已失败'
                : '-')}
        </Text>
      ),
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      width: 120,
      render: (model?: string) =>
        model ? (
          <Text code style={{ fontSize: 12 }}>
            {model}
          </Text>
        ) : (
          '-'
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: SubagentRun) => (
        <SubagentStop runId={record.id} status={record.status} onStop={onStop} />
      ),
    },
  ]

  if (runs.length === 0 && !loading) {
    return <EmptyState icon="🤖" description="暂无子代理运行" />
  }

  return (
    <Table
      columns={columns}
      dataSource={runs}
      rowKey="id"
      loading={loading}
      pagination={false}
      size="middle"
      onRow={(record) => ({
        onClick: () => onSelect(record.id),
        style: {
          cursor: 'pointer',
          background: record.id === selectedId ? 'var(--ant-color-primary-bg)' : undefined,
        },
      })}
    />
  )
}
