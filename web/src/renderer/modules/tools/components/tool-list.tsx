/** 工具注册表组件（Table） */

import { Table, Tag, Typography, Space, Switch, Button, Popconfirm, Tooltip } from 'antd'
import { EditOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { ToolInfo } from '../types/tools'
import { EmptyState } from '@/components/empty-state'
import styles from './tools-panel.module.css'

const { Text } = Typography

const RISK_MAP: Record<string, { label: string; color: string }> = {
  low: { label: '低', color: 'success' },
  medium: { label: '中', color: 'warning' },
  high: { label: '高', color: 'error' },
}

interface ToolListProps {
  tools: ToolInfo[]
  total: number
  page: number
  pageSize: number
  loading?: boolean
  onEdit?: (tool: ToolInfo) => void
  onDelete?: (id: number) => void
  onToggle?: (id: number, enable: boolean) => void
  onPageChange?: (page: number) => void
}

export function ToolList({ tools, total, page, pageSize, loading, onEdit, onDelete, onToggle, onPageChange }: ToolListProps) {
  const columns: ColumnsType<ToolInfo> = [
    {
      title: '工具名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <Text code strong>
            {record.displayName || name}
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {name}
          </Text>
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 260,
    },
    {
      title: '功能类别',
      dataIndex: 'module',
      key: 'module',
      width: 90,
      render: (module: string) => <Tag>{module}</Tag>,
    },
    {
      title: '风险',
      dataIndex: 'riskLevel',
      key: 'riskLevel',
      width: 80,
      render: (level: string) => {
        const { label, color } = RISK_MAP[level] ?? RISK_MAP.low
        return <Tag color={color}>{label}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'isEnabled',
      key: 'isEnabled',
      width: 80,
      render: (enabled: number, record) => (
        <Switch
          checked={enabled === 1}
          size="small"
          onChange={(checked) => onToggle?.(record.id, checked)}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      align: 'center',
      render: (_: unknown, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onEdit?.(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除此工具？"
            description="删除后不可恢复"
            onConfirm={() => onDelete?.(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="删除">
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
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
      size="middle"
      pagination={{
        current: page,
        pageSize,
        total,
        showTotal: (t) => `共 ${t} 个工具`,
        showSizeChanger: false,
        onChange: (p) => onPageChange?.(p),
      }}
    />
  )
}
