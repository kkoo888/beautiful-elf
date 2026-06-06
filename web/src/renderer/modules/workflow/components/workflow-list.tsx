/** 工作流列表组件 */

import { Table, Tag, Space, Button, Popconfirm, Typography } from 'antd'
import { PlayCircleOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Workflow, WorkflowStatus } from '../types/workflow'
import { EmptyState } from '@/components/empty-state'

const { Text } = Typography

const STATUS_MAP: Record<WorkflowStatus, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'default' },
  running: { label: '运行中', color: 'processing' },
  completed: { label: '已完成', color: 'success' },
  failed: { label: '失败', color: 'error' },
}

interface WorkflowListProps {
  workflows: Workflow[]
  loading?: boolean
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onRun: (id: string) => void
}

export function WorkflowList({ workflows, loading, onEdit, onDelete, onRun }: WorkflowListProps) {
  const columns: ColumnsType<Workflow> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Workflow) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          {record.description && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.description}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: WorkflowStatus) => {
        const { label, color } = STATUS_MAP[status]
        return <Tag color={color}>{label}</Tag>
      },
    },
    {
      title: '节点数',
      key: 'nodeCount',
      width: 80,
      align: 'center',
      render: (_: unknown, record: Workflow) => record.nodes.length,
    },
    {
      title: '最近运行',
      key: 'lastRun',
      width: 160,
      render: (_: unknown, record: Workflow) => {
        if (!record.lastRunAt) return <Text type="secondary">从未运行</Text>
        return (
          <Space size={4}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {new Date(record.lastRunAt).toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </Space>
        )
      },
    },
    {
      title: '运行次数',
      dataIndex: 'runCount',
      key: 'runCount',
      width: 90,
      align: 'center',
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: Workflow) => (
        <Space size={4}>
          <Button
            type="text"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => onRun(record.id)}
            title="运行"
          />
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => onEdit(record.id)}
            title="编辑"
          />
          <Popconfirm
            title="确定删除此工作流？"
            onConfirm={() => onDelete(record.id)}
            okText="删除"
            cancelText="取消"
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} title="删除" />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  if (workflows.length === 0 && !loading) {
    return <EmptyState icon="⚙️" description="暂无工作流" actionText="创建工作流" />
  }

  return (
    <Table
      columns={columns}
      dataSource={workflows}
      rowKey="id"
      loading={loading}
      pagination={false}
      size="middle"
    />
  )
}
