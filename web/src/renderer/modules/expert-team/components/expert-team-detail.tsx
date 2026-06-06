/** 专家团详情组件 */

import {
  Card,
  Descriptions,
  Tag,
  Space,
  Button,
  Typography,
  Avatar,
  List,
  Row,
  Col,
  Statistic,
  Switch,
  message,
} from 'antd'
import {
  EditOutlined,
  PlayCircleOutlined,
  UserOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { useCallback } from 'react'
import type { ExpertTeam } from '../types'
import { getExpertRoleColor } from '../types'
import { updateExpertTeam } from '../services/expert-team-api'

const { Title, Text, Paragraph } = Typography

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
    <div>
      {/* 头部信息 */}
      <Card>
        <Row justify="space-between" align="top">
          <Col>
            <Space align="start">
              <Avatar size={64} style={{ fontSize: 36, backgroundColor: '#f0f0f0' }}>
                {team.icon}
              </Avatar>
              <div>
                <Title level={4} style={{ margin: 0 }}>{team.teamName}</Title>
                <Space style={{ marginTop: 8 }}>
                  <Tag>{team.category}</Tag>
                  <Tag color="blue">v{team.version}</Tag>
                </Space>
                {team.description && (
                  <Paragraph type="secondary" style={{ marginTop: 8, maxWidth: 500 }}>
                    {team.description}
                  </Paragraph>
                )}
              </div>
            </Space>
          </Col>
          <Col>
            <Space direction="vertical" align="end" size="middle">
              <Space>
                <Text type="secondary">状态：</Text>
                <Switch
                  checked={team.isEnabled === 1}
                  onChange={handleToggleEnabled}
                  checkedChildren="启用"
                  unCheckedChildren="禁用"
                />
              </Space>
              <Space>
                <Button icon={<EditOutlined />} onClick={onEdit}>
                  编辑
                </Button>
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={onExecute}
                  disabled={team.members.length === 0 || team.isEnabled !== 1}
                >
                  执行
                </Button>
              </Space>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 统计信息 */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="专家成员"
              value={team.members.length}
              prefix={<UserOutlined />}
              suffix="人"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="最大讨论轮次"
              value={team.maxRounds}
              prefix={<ThunderboltOutlined />}
              suffix="轮"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="启用成员"
              value={team.members.filter((m) => m.isEnabled).length}
              suffix={`/ ${team.members.length}`}
            />
          </Card>
        </Col>
      </Row>

      {/* 专家成员列表 */}
      <Card title="👥 专家成员" style={{ marginTop: 16 }}>
        <List
          dataSource={team.members}
          renderItem={(member) => (
            <List.Item>
              <List.Item.Meta
                avatar={
                  <Avatar
                    style={{
                      backgroundColor: getExpertRoleColor(member.memberRole) + '20',
                      color: getExpertRoleColor(member.memberRole),
                      fontSize: 24,
                    }}
                  >
                    {member.avatar}
                  </Avatar>
                }
                title={
                  <Space>
                    <Text strong>{member.memberName}</Text>
                    <Tag color={getExpertRoleColor(member.memberRole)}>{member.memberRole}</Tag>
                    {!member.isEnabled && <Tag color="default">已禁用</Tag>}
                  </Space>
                }
                description={
                  <div>
                    <Paragraph
                      type="secondary"
                      ellipsis={{ rows: 2, tooltip: true }}
                      style={{ margin: 0 }}
                    >
                      {member.systemPrompt}
                    </Paragraph>
                    <Space style={{ marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        模型: {member.modelName || '默认'}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        温度: {(member.temperature / 100).toFixed(1)}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Max Tokens: {member.maxTokens}
                      </Text>
                    </Space>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </Card>

      {/* 提示词配置 */}
      <Card title="📝 提示词配置" style={{ marginTop: 16 }}>
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="编排器提示词">
            <Paragraph
              ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
              style={{ margin: 0 }}
            >
              {team.orchestratorPrompt || '（使用默认编排器提示词）'}
            </Paragraph>
          </Descriptions.Item>
          <Descriptions.Item label="汇总器提示词">
            <Paragraph
              ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
              style={{ margin: 0 }}
            >
              {team.synthesizerPrompt || '（使用默认汇总器提示词）'}
            </Paragraph>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}
