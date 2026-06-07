/** 专家团列表组件 */

import { Table, Tag, Space, Button, Popconfirm, Typography, Avatar, Tooltip } from 'antd'
import {
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { ExpertTeam } from '../types'
import { EmptyState } from '@/components/empty-state'

const { Text } = Typography

interface ExpertTeamListProps {
  teams: ExpertTeam[]
  loading?: boolean
  onView: (id: number) => void
  onEdit: (id: number) => void
  onDelete: (id: number) => void
  onExecute: (team: ExpertTeam) => void
}

export function ExpertTeamList({
  teams,
  loading,
  onView,
  onEdit,
  onDelete,
  onExecute,
}: ExpertTeamListProps) {
  const columns: ColumnsType<ExpertTeam> = [
    {
      title: '专家团',
      key: 'name',
      render: (_: unknown, record: ExpertTeam) => (
        <Space>
          <Avatar size={40} style={{ fontSize: 24, backgroundColor: '#f0f0f0' }}>
            {record.icon}
          </Avatar>
          <Space orientation="vertical" size={0}>
            <Text strong>{record.teamName}</Text>
            {record.description && (
              <Text type="secondary" style={{ fontSize: 12 }} ellipsis={{ tooltip: true }}>
                {record.description}
              </Text>
            )}
          </Space>
        </Space>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (category: string) => <Tag>{category}</Tag>,
    },
    {
      title: '专家成员',
      key: 'members',
      width: 200,
      render: (_: unknown, record: ExpertTeam) => (
        <Space size={4} wrap>
          {record.members.slice(0, 5).map((m) => (
            <Tooltip key={m.id} title={`${m.memberName} (${m.memberRole})`}>
              <Avatar size={28} style={{ fontSize: 16, backgroundColor: '#e6f7ff' }}>
                {m.avatar}
              </Avatar>
            </Tooltip>
          ))}
          {record.members.length > 5 && (
            <Tag>+{record.members.length - 5}</Tag>
          )}
          {record.members.length === 0 && (
            <Text type="secondary" style={{ fontSize: 12 }}>暂无成员</Text>
          )}
        </Space>
      ),
    },
    {
      title: '最大轮次',
      dataIndex: 'maxRounds',
      key: 'maxRounds',
      width: 100,
      align: 'center',
      render: (rounds: number) => <Tag color="blue">{rounds} 轮</Tag>,
    },
    {
      title: '状态',
      key: 'status',
      width: 80,
      render: (_: unknown, record: ExpertTeam) => (
        <Tag color={record.isEnabled ? 'green' : 'default'}>
          {record.isEnabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: ExpertTeam) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onView(record.id)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => onExecute(record)}
            disabled={record.members.length === 0}
          >
            执行
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => onEdit(record.id)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此专家团？"
            onConfirm={() => onDelete(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  if (!loading && teams.length === 0) {
    return (
      <EmptyState
        description="还没有专家团，点击上方按钮创建一个吧"
        icon="👥"
      />
    )
  }

  return (
    <Table
      columns={columns}
      dataSource={teams}
      rowKey="id"
      loading={loading}
      pagination={false}
      onRow={(record) => ({
        onClick: () => onView(record.id),
        style: { cursor: 'pointer' },
      })}
    />
  )
}
