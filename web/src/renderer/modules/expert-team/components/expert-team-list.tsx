/** 专家团列表组件 — 卡片网格 */

import { Card, Tag, Space, Button, Popconfirm, Typography, Avatar, Tooltip, Spin } from 'antd'
import {
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import type { ExpertTeam } from '../types'
import { EmptyState } from '@/components/empty-state'
import styles from './expert-team.module.css'

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
  if (loading && teams.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  if (!loading && teams.length === 0) {
    return (
      <EmptyState
        description="还没有专家团，点击上方按钮创建一个吧"
        icon="👥"
      />
    )
  }

  return (
    <div className={styles.cardGrid}>
      {teams.map((team) => (
        <Card
          key={team.id}
          className={styles.teamCard}
          hoverable
          styles={{ body: { padding: '20px' } }}
          onClick={() => onView(team.id)}
        >
          {/* 头部：图标 + 名称 + 描述 */}
          <div className={styles.teamCardHeader}>
            <div className={styles.teamCardAvatar}>{team.icon}</div>
            <div className={styles.teamCardInfo}>
              <div className={styles.teamCardName}>{team.teamName}</div>
              {team.description && (
                <div className={styles.teamCardDesc}>{team.description}</div>
              )}
            </div>
            <Tag color={team.isEnabled ? 'green' : 'default'} style={{ margin: 0 }}>
              {team.isEnabled ? '启用' : '禁用'}
            </Tag>
          </div>

          {/* 标签区 */}
          <div className={styles.teamCardMeta}>
            <Tag>{team.category}</Tag>
            <Tag color="blue">v{team.version}</Tag>
            <Tag color="geekblue">{team.maxRounds} 轮</Tag>
          </div>

          {/* 成员头像行 + 操作按钮 */}
          <div className={styles.teamCardMembers}>
            <Space size={0}>
              {team.members.slice(0, 6).map((m) => (
                <Tooltip key={m.id} title={`${m.memberName} (${m.memberRole})`}>
                  <Avatar
                    size={28}
                    style={{ fontSize: 14, backgroundColor: '#e6f7ff', marginRight: -4 }}
                  >
                    {m.avatar}
                  </Avatar>
                </Tooltip>
              ))}
              {team.members.length > 6 && (
                <Tag style={{ marginLeft: 8 }}>+{team.members.length - 6}</Tag>
              )}
              {team.members.length === 0 && (
                <Text type="secondary" style={{ fontSize: 12 }}>暂无成员</Text>
              )}
            </Space>
            <div className={styles.teamCardActions} onClick={(e) => e.stopPropagation()}>
              <Tooltip title="查看详情">
                <Button type="text" size="small" icon={<EyeOutlined />} onClick={() => onView(team.id)} />
              </Tooltip>
              <Tooltip title="执行">
                <Button
                  type="text"
                  size="small"
                  icon={<PlayCircleOutlined />}
                  onClick={() => onExecute(team)}
                  disabled={team.members.length === 0}
                />
              </Tooltip>
              <Tooltip title="编辑">
                <Button type="text" size="small" icon={<EditOutlined />} onClick={() => onEdit(team.id)} />
              </Tooltip>
              <Popconfirm title="确定删除此专家团？" onConfirm={() => onDelete(team.id)}>
                <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
              </Popconfirm>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
