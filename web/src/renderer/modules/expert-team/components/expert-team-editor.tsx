/** 专家团编辑器组件 */

import { useState, useCallback } from 'react'
import {
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Space,
  Card,
  Typography,
  Divider,
  Popconfirm,
  message,
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import type { ExpertTeam, ExpertTeamFormInput, ExpertMemberFormInput } from '../types'

const { TextArea } = Input
const { Text } = Typography

/** 预设专家角色 */
const PRESET_EXPERTS: ExpertMemberFormInput[] = [
  {
    name: '架构师',
    role: '架构师',
    avatar: '🏗️',
    systemPrompt: '你是一位资深软件架构师，擅长系统设计、技术选型、性能优化。请从架构角度分析问题，关注可扩展性、可维护性和性能。',
  },
  {
    name: '测试专家',
    role: '测试专家',
    avatar: '🧪',
    systemPrompt: '你是一位经验丰富的测试专家，擅长发现潜在问题、设计测试策略。请从质量保障角度分析问题，关注边界情况、异常场景和回归风险。',
  },
  {
    name: '产品经理',
    role: '产品经理',
    avatar: '📋',
    systemPrompt: '你是一位敏锐的产品经理，擅长用户需求分析、产品规划。请从用户体验和商业价值角度分析问题，关注用户痛点和市场竞争力。',
  },
  {
    name: '安全专家',
    role: '安全专家',
    avatar: '🛡️',
    systemPrompt: '你是一位安全专家，擅长安全审计、风险评估。请从安全角度分析问题，关注数据安全、权限控制和潜在攻击面。',
  },
  {
    name: '数据专家',
    role: '数据专家',
    avatar: '📊',
    systemPrompt: '你是一位数据专家，擅长数据分析、数据建模。请从数据角度分析问题，关注数据质量、数据流和指标体系。',
  },
]

interface ExpertTeamEditorProps {
  team?: ExpertTeam
  onSave: (input: ExpertTeamFormInput) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export function ExpertTeamEditor({ team, onSave, onCancel, loading }: ExpertTeamEditorProps) {
  const [form] = Form.useForm()
  const [members, setMembers] = useState<ExpertMemberFormInput[]>(
    team?.members.map((m) => ({
      name: m.name,
      role: m.role,
      avatar: m.avatar,
      systemPrompt: m.systemPrompt,
      modelName: m.modelName,
      temperature: m.temperature,
      maxTokens: m.maxTokens,
    })) ?? []
  )

  const handleAddMember = useCallback(() => {
    setMembers((prev) => [
      ...prev,
      {
        name: '',
        role: '',
        avatar: '🤖',
        systemPrompt: '',
        temperature: 70,
        maxTokens: 2048,
      },
    ])
  }, [])

  const handleAddPreset = useCallback((preset: ExpertMemberFormInput) => {
    setMembers((prev) => {
      if (prev.some((m) => m.role === preset.role)) {
        message.warning(`已存在「${preset.role}」角色`)
        return prev
      }
      return [...prev, { ...preset }]
    })
  }, [])

  const handleRemoveMember = useCallback((index: number) => {
    setMembers((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleMemberChange = useCallback(
    (index: number, field: keyof ExpertMemberFormInput, value: unknown) => {
      setMembers((prev) =>
        prev.map((m, i) => (i === index ? { ...m, [field]: value } : m))
      )
    },
    []
  )

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields()

      if (members.length === 0) {
        message.warning('请至少添加一位专家成员')
        return
      }

      for (let i = 0; i < members.length; i++) {
        if (!members[i].name || !members[i].role || !members[i].systemPrompt) {
          message.warning(`专家 #${i + 1} 的名称、角色和提示词不能为空`)
          return
        }
      }

      const input: ExpertTeamFormInput = {
        name: values.name,
        description: values.description ?? '',
        icon: values.icon ?? '👥',
        category: values.category ?? '通用',
        orchestratorPrompt: values.orchestratorPrompt ?? '',
        synthesizerPrompt: values.synthesizerPrompt ?? '',
        maxRounds: values.maxRounds ?? 3,
        members,
      }

      await onSave(input)
    } catch {
      // form validation failed
    }
  }, [form, members, onSave])

  return (
    <div>
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          name: team?.name ?? '',
          description: team?.description ?? '',
          icon: team?.icon ?? '👥',
          category: team?.category ?? '通用',
          orchestratorPrompt: team?.orchestratorPrompt ?? '',
          synthesizerPrompt: team?.synthesizerPrompt ?? '',
          maxRounds: team?.maxRounds ?? 3,
        }}
      >
        {/* 基本信息 */}
        <Card title="📝 基本信息">
          <Space style={{ width: '100%' }} size="large" align="start" wrap>
            <Form.Item name="icon" label="图标" style={{ width: 100 }}>
              <Input placeholder="👥" style={{ textAlign: 'center', fontSize: 24 }} />
            </Form.Item>
            <Form.Item
              name="name"
              label="专家团名称"
              rules={[{ required: true, message: '请输入名称' }]}
              style={{ flex: 1, minWidth: 200 }}
            >
              <Input placeholder="例如: 产品评审专家团" />
            </Form.Item>
            <Form.Item name="category" label="分类" style={{ width: 150 }}>
              <Select
                options={[
                  { label: '通用', value: '通用' },
                  { label: '技术', value: '技术' },
                  { label: '产品', value: '产品' },
                  { label: '设计', value: '设计' },
                  { label: '安全', value: '安全' },
                  { label: '数据', value: '数据' },
                ]}
              />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="这个专家团用来做什么..." />
          </Form.Item>
        </Card>

        {/* 提示词配置 */}
        <Card title="🧠 提示词配置" style={{ marginTop: 16 }}>
          <Form.Item name="orchestratorPrompt" label="编排器提示词（可选）">
            <TextArea
              rows={3}
              placeholder="留空使用默认编排器。自定义编排器可以控制任务分配策略..."
            />
          </Form.Item>
          <Form.Item name="synthesizerPrompt" label="汇总器提示词（可选）">
            <TextArea
              rows={3}
              placeholder="留空使用默认汇总器。自定义汇总器可以控制输出格式和风格..."
            />
          </Form.Item>
          <Form.Item name="maxRounds" label="最大讨论轮次">
            <InputNumber min={1} max={10} style={{ width: 120 }} />
          </Form.Item>
        </Card>

        {/* 专家成员 */}
        <Card
          title={
            <Space>
              <span>👥 专家成员</span>
              <Text type="secondary">({members.length} 人)</Text>
            </Space>
          }
          extra={
            <Space>
              <Select
                placeholder="快速添加预设专家"
                style={{ width: 200 }}
                onChange={(value) => {
                  const preset = PRESET_EXPERTS.find((p) => p.role === value)
                  if (preset) handleAddPreset(preset)
                }}
                options={PRESET_EXPERTS.map((p) => ({
                  label: `${p.avatar} ${p.name}`,
                  value: p.role,
                }))}
                allowClear
              />
              <Button icon={<UserAddOutlined />} onClick={handleAddMember}>
                自定义专家
              </Button>
            </Space>
          }
          style={{ marginTop: 16 }}
        >
          {members.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Text type="secondary">暂无专家成员，请点击上方按钮添加</Text>
            </div>
          ) : (
            members.map((member, index) => (
              <Card
                key={index}
                size="small"
                style={{ marginBottom: 12 }}
                title={
                  <Space>
                    <span style={{ fontSize: 20 }}>{member.avatar || '🤖'}</span>
                    <Text strong>{member.name || `专家 #${index + 1}`}</Text>
                    {member.role && (
                      <Text type="secondary">({member.role})</Text>
                    )}
                  </Space>
                }
                extra={
                  <Popconfirm
                    title="确定移除此专家？"
                    onConfirm={() => handleRemoveMember(index)}
                  >
                    <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                  </Popconfirm>
                }
              >
                <Space style={{ width: '100%' }} size="middle" align="start" wrap>
                  <Form.Item label="头像" style={{ width: 80, marginBottom: 8 }}>
                    <Input
                      value={member.avatar}
                      onChange={(e) => handleMemberChange(index, 'avatar', e.target.value)}
                      style={{ textAlign: 'center', fontSize: 20 }}
                    />
                  </Form.Item>
                  <Form.Item label="名称" required style={{ flex: 1, minWidth: 120, marginBottom: 8 }}>
                    <Input
                      value={member.name}
                      onChange={(e) => handleMemberChange(index, 'name', e.target.value)}
                      placeholder="专家名称"
                    />
                  </Form.Item>
                  <Form.Item label="角色" required style={{ flex: 1, minWidth: 120, marginBottom: 8 }}>
                    <Input
                      value={member.role}
                      onChange={(e) => handleMemberChange(index, 'role', e.target.value)}
                      placeholder="如: 架构师"
                    />
                  </Form.Item>
                </Space>
                <Form.Item label="系统提示词" required style={{ marginBottom: 8 }}>
                  <TextArea
                    value={member.systemPrompt}
                    onChange={(e) => handleMemberChange(index, 'systemPrompt', e.target.value)}
                    rows={3}
                    placeholder="定义这个专家的专业领域和行为方式..."
                  />
                </Form.Item>
                <Space>
                  <Form.Item label="模型" style={{ marginBottom: 0 }}>
                    <Input
                      value={member.modelName}
                      onChange={(e) => handleMemberChange(index, 'modelName', e.target.value)}
                      placeholder="默认模型"
                      style={{ width: 150 }}
                    />
                  </Form.Item>
                  <Form.Item label="温度" style={{ marginBottom: 0 }}>
                    <InputNumber
                      value={member.temperature}
                      onChange={(v) => handleMemberChange(index, 'temperature', v)}
                      min={0}
                      max={200}
                      style={{ width: 100 }}
                    />
                  </Form.Item>
                  <Form.Item label="Max Tokens" style={{ marginBottom: 0 }}>
                    <InputNumber
                      value={member.maxTokens}
                      onChange={(v) => handleMemberChange(index, 'maxTokens', v)}
                      min={1}
                      max={8192}
                      style={{ width: 120 }}
                    />
                  </Form.Item>
                </Space>
              </Card>
            ))
          )}
        </Card>
      </Form>

      {/* 底部操作栏 */}
      <Divider />
      <div style={{ textAlign: 'right' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={onCancel}>
            取消
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSubmit}
            loading={loading}
          >
            {team ? '保存修改' : '创建专家团'}
          </Button>
        </Space>
      </div>
    </div>
  )
}
