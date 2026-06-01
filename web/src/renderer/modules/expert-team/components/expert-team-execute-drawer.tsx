/** 专家团执行抽屉组件 */

import { Drawer, Form, Input, InputNumber, Button, Space, Typography, Tag } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { useEffect } from 'react'
import type { ExpertTeam, ExpertTeamExecuteInput } from '../types'

const { TextArea } = Input
const { Text } = Typography

interface ExpertTeamExecuteDrawerProps {
  open: boolean
  team: ExpertTeam | null
  onClose: () => void
  onSubmit: (input: ExpertTeamExecuteInput) => Promise<void>
  loading?: boolean
}

export function ExpertTeamExecuteDrawer({
  open,
  team,
  onClose,
  onSubmit,
  loading,
}: ExpertTeamExecuteDrawerProps) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (open) {
      form.resetFields()
    }
  }, [open, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      await onSubmit({
        inputText: values.inputText,
        maxRounds: values.maxRounds,
      })
    } catch {
      // validation failed
    }
  }

  if (!team) return null

  return (
    <Drawer
      title={
        <Space>
          <span style={{ fontSize: 24 }}>{team.icon}</span>
          <span>执行「{team.name}」</span>
        </Space>
      }
      open={open}
      onClose={onClose}
      width={520}
      extra={
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleSubmit}
          loading={loading}
        >
          开始执行
        </Button>
      }
    >
      {/* 专家团信息 */}
      <div
        style={{
          background: '#f5f5f5',
          borderRadius: 8,
          padding: 16,
          marginBottom: 24,
        }}
      >
        <Text type="secondary" style={{ fontSize: 12 }}>参与专家</Text>
        <div style={{ marginTop: 8 }}>
          <Space wrap>
            {team.members
              .filter((m) => m.enabled)
              .map((m) => (
                <Tag key={m.id} style={{ padding: '4px 8px' }}>
                  <Space size={4}>
                    <span>{m.avatar}</span>
                    <span>{m.name}</span>
                    <Text type="secondary">({m.role})</Text>
                  </Space>
                </Tag>
              ))}
          </Space>
        </div>
        <div style={{ marginTop: 8 }}>
          <Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              最大讨论轮次: <Tag color="blue">{team.maxRounds} 轮</Tag>
            </Text>
          </Space>
        </div>
      </div>

      {/* 执行表单 */}
      <Form form={form} layout="vertical">
        <Form.Item
          name="inputText"
          label="输入问题/任务"
          rules={[{ required: true, message: '请输入要分析的问题或任务' }]}
        >
          <TextArea
            rows={6}
            placeholder="描述你需要专家团分析的问题或任务...&#10;&#10;例如: 请分析我们项目的微服务架构改造方案，评估技术风险和实施路径。"
          />
        </Form.Item>

        <Form.Item name="maxRounds" label="覆盖最大轮次（可选）">
          <InputNumber
            min={1}
            max={10}
            placeholder={`默认: ${team.maxRounds}`}
            style={{ width: 160 }}
          />
        </Form.Item>
      </Form>

      {/* 执行说明 */}
      <div
        style={{
          background: '#e6f7ff',
          borderRadius: 8,
          padding: 12,
          marginTop: 16,
        }}
      >
        <Text style={{ fontSize: 13 }}>
          💡 执行流程：编排器分析任务 → 各专家并行讨论（最多{' '}
          <Tag color="blue">{team.maxRounds}</Tag> 轮）→ 汇总器生成最终报告
        </Text>
      </div>
    </Drawer>
  )
}
