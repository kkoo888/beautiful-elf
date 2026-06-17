/** 专家团详情组件 */

import {
  Card,
  Tag,
  Space,
  Button,
  Typography,
  Statistic,
  Switch,
  Collapse,
  message,
} from 'antd'
import {
  EditOutlined,
  PlayCircleOutlined,
  UserOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  CrownOutlined,
} from '@ant-design/icons'
import { useCallback } from 'react'
import type { ExpertTeam } from '../types'
import { getExpertRoleColor } from '../types'
import { updateExpertTeam } from '../services/expert-team-api'
import { ExpertAvatar } from '@/components/expert-avatar'
import styles from './expert-team.module.css'

const { Text, Paragraph } = Typography

interface ExpertTeamDetailProps {
  team: ExpertTeam
  onEdit: () => void
  onExecute: () => void
  onRefresh?: () => void
}

export function ExpertTeamDetail({ team, onEdit, onExecute, onRefresh }: ExpertTeamDetailProps) {
  const handleToggleEnabled = useCallback(async (checked: boolean) => {
    try {
      await updateExpertTeam(team.id, { isEnabled: checked ? 1 : 0 })
      message.success(checked ? '已启用' : '已禁用')
      onRefresh?.()
    } catch {
      message.error('操作失败')
    }
  }, [team.id, onRefresh])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* 头部信息 */}
      <Card>
        <div className={styles.detailHeader}>
          <Space align="start" size={16}>
            <div
              className={styles.detailAvatar}
              style={{
                backgroundColor: team.icon?.startsWith('data:image') ? 'transparent' : undefined,
                overflow: 'hidden',
              }}
            >
              {team.icon?.startsWith('data:image') ? (
                <img src={team.icon} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                team.icon
              )}
            </div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, lineHeight: 1.4 }}>
                {team.teamName}
              </div>
              <Space style={{ marginTop: 6 }}>
                <Tag>{team.category}</Tag>
                <Tag color="blue">v{team.version}</Tag>
                <Tag color={team.isEnabled ? 'green' : 'default'}>
                  {team.isEnabled ? '启用' : '禁用'}
                </Tag>
              </Space>
              {team.description && (
                <Paragraph type="secondary" style={{ marginTop: 8, maxWidth: 500, margin: 0 }}>
                  {team.description}
                </Paragraph>
              )}
              {team.leader && (
                <div style={{ marginTop: 6 }}>
                  <Tag color="gold">
                    <CrownOutlined style={{ marginRight: 4 }} /> 组长: {team.leader.memberName}（{team.leader.memberRole}）
                  </Tag>
                </div>
              )}
            </div>
          </Space>
          <div className={styles.detailActions}>
            <Space>
              <Text type="secondary">状态</Text>
              <Switch
                checked={team.isEnabled === 1}
                onChange={handleToggleEnabled}
                checkedChildren="启用"
                unCheckedChildren="禁用"
              />
            </Space>
            <Space>
              <Button icon={<EditOutlined />} onClick={onEdit}>编辑</Button>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={onExecute}
                disabled={team.experts.length === 0 || team.isEnabled !== 1}
              >
                执行
              </Button>
            </Space>
          </div>
        </div>
      </Card>

      {/* 统计信息 */}
      <div className={styles.statGrid}>
        <Card>
          <Statistic title="专家成员" value={team.experts.length} prefix={<UserOutlined />} suffix="人" />
        </Card>
        <Card>
          <Statistic title="最大讨论轮次" value={team.maxRounds} prefix={<ThunderboltOutlined />} suffix="轮" />
        </Card>
        <Card>
          <Statistic
            title="启用成员"
            value={team.experts.filter((m) => m.isEnabled).length}
            suffix={`/ ${team.experts.length}`}
          />
        </Card>
      </div>

      {/* 绑定的专家列表 */}
      <Card title="👥 绑定专家" styles={{ body: { padding: '12px 16px' } }}>
        {team.experts.map((member) => {
          const roleColor = getExpertRoleColor(member.memberRole)
          return (
            <div
              key={member.id}
              className={styles.memberListCard}
              style={{ borderLeft: `3px solid ${roleColor}` }}
            >
              <div className={styles.memberListCardHeader}>
                <ExpertAvatar
                  avatar={member.avatar}
                  size={40}
                  bgColor={roleColor + '18'}
                  color={roleColor}
                  className={styles.memberAvatar}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Space>
                    <Text strong>{member.memberName}</Text>
                    <Tag color={roleColor} style={{ margin: 0 }}>{member.memberRole}</Tag>
                    {!member.isEnabled && <Tag color="default">已禁用</Tag>}
                  </Space>
                </div>
              </div>
              <p className={styles.memberPrompt}>{member.systemPrompt}</p>
              <div className={styles.memberMeta}>
                <span>模型: {member.modelName || '默认'}</span>
                <span>温度: {member.temperature.toFixed(1)}</span>
                <span>Max Tokens: {member.maxTokens}</span>
              </div>
            </div>
          )
        })}
        {team.experts.length === 0 && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <Text type="secondary">暂未绑定专家</Text>
          </div>
        )}
      </Card>

      {/* 提示词配置 */}
      <Collapse
        items={[
          {
            key: 'prompts',
            label: (
              <Space>
                <FileTextOutlined />
                <span>📝 提示词配置</span>
              </Space>
            ),
            children: (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div>
                  <Text strong style={{ fontSize: 13 }}>编排器提示词</Text>
                  <Paragraph
                    type="secondary"
                    ellipsis={{ rows: 4, expandable: true, symbol: '展开' }}
                    style={{ marginTop: 4, marginBottom: 0 }}
                  >
                    {team.orchestratorPrompt || '（使用默认编排器提示词）'}
                  </Paragraph>
                </div>
                <div>
                  <Text strong style={{ fontSize: 13 }}>汇总器提示词</Text>
                  <Paragraph
                    type="secondary"
                    ellipsis={{ rows: 4, expandable: true, symbol: '展开' }}
                    style={{ marginTop: 4, marginBottom: 0 }}
                  >
                    {team.synthesizerPrompt || '（使用默认汇总器提示词）'}
                  </Paragraph>
                </div>
              </div>
            ),
          },
        ]}
      />
    </div>
  )
}
