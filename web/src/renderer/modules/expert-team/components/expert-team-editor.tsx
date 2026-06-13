/** 专家团编辑器组件 */

import { useState, useCallback, useEffect } from 'react'
import {
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Space,
  Card,
  Typography,
  Popconfirm,
  Switch,
  Modal,
  message,
} from 'antd'
import {
  DeleteOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  UserAddOutlined,
  EditOutlined,
} from '@ant-design/icons'
import { CompactModelSelect } from '@/modules/shared/components/model-selector'
import type { ExpertTeam, ExpertTeamFormInput, ExpertMemberFormInput } from '../types'
import { getExpertRoleColor } from '../types'
import styles from './expert-team.module.css'

const { TextArea } = Input
const { Text } = Typography

/** 预设头像列表 */
const PRESET_AVATARS = [
  '🤖', '👨‍💻', '👩‍💻', '🏗️', '🧪', '📋', '🛡️', '📊',
  '🎨', '🔬', '🎯', '💡', '🔍', '📝', '🧠', '👨‍🔬',
  '👩‍🔬', '👨‍🏫', '👩‍🏫', '🧙‍♂️', '🦾', '👁️', '🗣️', '🤝',
  '🎭', '⚖️', '📈', '🗄️', '🌐', '🔧', '⚙️', '🚀',
]

/** 专家团图标列表 */
const TEAM_ICONS = [
  '👥', '🧠', '🏗️', '🔬', '🎯', '💡', '🚀', '⚡',
  '🌐', '📊', '🛡️', '🎨', '🤖', '🔧', '⚙️', '📋',
]

/** 预设专家角色 */
const PRESET_EXPERTS: ExpertMemberFormInput[] = [
  {
    memberName: '架构师',
    memberRole: '架构师',
    avatar: '🏗️',
    systemPrompt: '你是一位资深软件架构师，擅长系统设计、技术选型、性能优化。请从架构角度分析问题，关注可扩展性、可维护性和性能。',
  },
  {
    memberName: '测试专家',
    memberRole: '测试专家',
    avatar: '🧪',
    systemPrompt: '你是一位经验丰富的测试专家，擅长发现潜在问题、设计测试策略。请从质量保障角度分析问题，关注边界情况、异常场景和回归风险。',
  },
  {
    memberName: '产品经理',
    memberRole: '产品经理',
    avatar: '📋',
    systemPrompt: '你是一位敏锐的产品经理，擅长用户需求分析、产品规划。请从用户体验和商业价值角度分析问题，关注用户痛点和市场竞争力。',
  },
  {
    memberName: '安全专家',
    memberRole: '安全专家',
    avatar: '🛡️',
    systemPrompt: '你是一位安全专家，擅长安全审计、风险评估。请从安全角度分析问题，关注数据安全、权限控制和潜在攻击面。',
  },
  {
    memberName: '数据专家',
    memberRole: '数据专家',
    avatar: '📊',
    systemPrompt: '你是一位数据专家，擅长数据分析、数据建模。请从数据角度分析问题，关注数据质量、数据流和指标体系。',
  },
]

/** Emoji 网格选择器（用于弹窗内） */
function EmojiGrid({
  value,
  options,
  onChange,
}: {
  value: string
  options: string[]
  onChange: (v: string) => void
}) {
  return (
    <div className={styles.modalEmojiGrid}>
      {options.map((emoji) => (
        <div
          key={emoji}
          className={`${styles.emojiItem} ${value === emoji ? styles.emojiItemSelected : ''}`}
          onClick={() => onChange(emoji)}
        >
          {emoji}
        </div>
      ))}
    </div>
  )
}

/** 成员编辑弹窗 */
function MemberEditModal({
  open,
  member,
  isNew,
  onOk,
  onCancel,
}: {
  open: boolean
  member: ExpertMemberFormInput | null
  isNew: boolean
  onOk: (updated: ExpertMemberFormInput) => void
  onCancel: () => void
}) {
  const [form] = Form.useForm()
  const [avatar, setAvatar] = useState(member?.avatar ?? '🤖')
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)

  useEffect(() => {
    if (open && member) {
      setAvatar(member.avatar ?? '🤖')
      form.setFieldsValue({
        memberName: member.memberName,
        memberRole: member.memberRole,
        systemPrompt: member.systemPrompt,
        modelName: member.modelName || '',
        temperature: member.temperature,
        maxTokens: member.maxTokens,
        isEnabled: member.isEnabled !== 0,
      })
    }
  }, [open, member, form])

  const handleOk = useCallback(async () => {
    try {
      const values = await form.validateFields()
      onOk({
        memberName: values.memberName,
        memberRole: values.memberRole,
        avatar,
        systemPrompt: values.systemPrompt,
        modelName: values.modelName || undefined,
        temperature: values.temperature,
        maxTokens: values.maxTokens,
        isEnabled: values.isEnabled ? 1 : 0,
      })
    } catch {
      // validation failed
    }
  }, [form, avatar, onOk])

  const roleColor = member ? getExpertRoleColor(member.memberRole) : '#d9d9d9'

  return (
    <Modal
      open={open}
      title={isNew ? '添加专家成员' : '编辑专家成员'}
      onOk={handleOk}
      onCancel={onCancel}
      width={600}
      okText="确定"
      cancelText="取消"
      destroyOnHidden
    >
      {/* 头像区域 */}
      <div className={styles.modalAvatarWrap}>
        <div
          className={styles.modalAvatarLarge}
          style={{ backgroundColor: roleColor + '18', color: roleColor }}
          onClick={() => setShowEmojiPicker(!showEmojiPicker)}
        >
          {avatar}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 16 }}>
            {member?.memberName || '新专家'}
          </div>
          <Text type="secondary" style={{ fontSize: 13 }}>
            {member?.memberRole || '点击头像更换'}
          </Text>
        </div>
      </div>

      {showEmojiPicker && (
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
            选择头像（点击选中，再次点击收起）
          </Text>
          <EmojiGrid
            value={avatar}
            options={PRESET_AVATARS}
            onChange={(v) => {
              setAvatar(v)
              setShowEmojiPicker(false)
            }}
          />
        </div>
      )}

      <Form form={form} layout="vertical">
        <div style={{ display: 'flex', gap: 12 }}>
          <Form.Item
            name="memberName"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
            style={{ flex: 1 }}
          >
            <Input placeholder="专家名称" />
          </Form.Item>
          <Form.Item
            name="memberRole"
            label="角色"
            rules={[{ required: true, message: '请输入角色' }]}
            style={{ flex: 1 }}
          >
            <Input placeholder="如: 架构师" />
          </Form.Item>
        </div>

        <Form.Item
          name="systemPrompt"
          label="系统提示词"
          rules={[{ required: true, message: '请输入系统提示词' }]}
        >
          <TextArea rows={5} placeholder="定义这个专家的专业领域和行为方式..." />
        </Form.Item>

        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <Form.Item label="模型" style={{ flex: 1, minWidth: 200 }}>
            <CompactModelSelect
              value={form.getFieldValue('modelName') || ''}
              onChange={(_val, _pid, modelName) => form.setFieldValue('modelName', modelName)}
              placeholder="默认模型"
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Form.Item label="温度" name="temperature" initialValue={0.7}>
            <InputNumber min={0} max={2} step={0.1} style={{ width: 100 }} />
          </Form.Item>
          <Form.Item label="Max Tokens" name="maxTokens" initialValue={2048}>
            <InputNumber min={1} max={8192} style={{ width: 120 }} />
          </Form.Item>
        </div>

        <Form.Item name="isEnabled" label="启用状态" valuePropName="checked" initialValue={true}>
          <Switch checkedChildren="启用" unCheckedChildren="禁用" />
        </Form.Item>
      </Form>
    </Modal>
  )
}

interface ExpertTeamEditorProps {
  team?: ExpertTeam
  onSave: (input: ExpertTeamFormInput) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export function ExpertTeamEditor({ team, onSave, onCancel, loading }: ExpertTeamEditorProps) {
  const [form] = Form.useForm()
  const [teamIcon, setTeamIcon] = useState(team?.icon ?? '👥')
  const [showTeamIconPicker, setShowTeamIconPicker] = useState(false)
  const [members, setMembers] = useState<ExpertMemberFormInput[]>(
    team?.members.map((m) => ({
      memberName: m.memberName,
      memberRole: m.memberRole,
      avatar: m.avatar,
      systemPrompt: m.systemPrompt,
      modelName: m.modelName,
      temperature: m.temperature,
      maxTokens: m.maxTokens,
      isEnabled: m.isEnabled ?? 1,
    })) ?? []
  )

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)

  const openEditModal = useCallback((index: number) => {
    setEditingIndex(index)
    setModalOpen(true)
  }, [])

  const openAddModal = useCallback(() => {
    setEditingIndex(null)
    setModalOpen(true)
  }, [])

  const handleModalOk = useCallback((updated: ExpertMemberFormInput) => {
    if (editingIndex !== null) {
      // Update existing
      setMembers((prev) =>
        prev.map((m, i) => (i === editingIndex ? updated : m))
      )
    } else {
      // Add new
      setMembers((prev) => [...prev, updated])
    }
    setModalOpen(false)
    setEditingIndex(null)
  }, [editingIndex])

  const handleModalCancel = useCallback(() => {
    setModalOpen(false)
    setEditingIndex(null)
  }, [])

  const handleAddPreset = useCallback((preset: ExpertMemberFormInput) => {
    setMembers((prev) => {
      if (prev.some((m) => m.memberRole === preset.memberRole)) {
        message.warning(`已存在「${preset.memberRole}」角色`)
        return prev
      }
      return [...prev, { ...preset, enabled: 1 }]
    })
  }, [])

  const handleRemoveMember = useCallback((index: number) => {
    setMembers((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields()

      if (members.length === 0) {
        message.warning('请至少添加一位专家成员')
        return
      }

      for (let i = 0; i < members.length; i++) {
        if (!members[i].memberName || !members[i].memberRole || !members[i].systemPrompt) {
          message.warning(`专家 #${i + 1} 的名称、角色和提示词不能为空`)
          return
        }
      }

      const input: ExpertTeamFormInput = {
        teamName: values.teamName,
        description: values.description ?? '',
        icon: teamIcon,
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
  }, [form, members, teamIcon, onSave])

  // Current member being edited in modal
  const editingMember = editingIndex !== null ? members[editingIndex] : null
  const isNewMember = editingIndex === null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          teamName: team?.teamName ?? '',
          description: team?.description ?? '',
          category: team?.category ?? '通用',
          orchestratorPrompt: team?.orchestratorPrompt ?? '',
          synthesizerPrompt: team?.synthesizerPrompt ?? '',
          maxRounds: team?.maxRounds ?? 3,
        }}
      >
        {/* 基本信息 */}
        <Card title="📝 基本信息">
          <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
            {/* 图标选择 */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
              <div
                className={styles.iconPreview}
                style={{ cursor: 'pointer' }}
                onClick={() => setShowTeamIconPicker(!showTeamIconPicker)}
              >
                {teamIcon}
              </div>
              <Text type="secondary" style={{ fontSize: 11 }}>点击更换</Text>
              {showTeamIconPicker && (
                <EmojiGrid
                  value={teamIcon}
                  options={TEAM_ICONS}
                  onChange={(v) => {
                    setTeamIcon(v)
                    setShowTeamIconPicker(false)
                  }}
                />
              )}
            </div>

            {/* 名称和分类 */}
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', gap: 12 }}>
                <Form.Item
                  name="teamName"
                  label="专家团名称"
                  rules={[{ required: true, message: '请输入名称' }]}
                  style={{ flex: 1 }}
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
              </div>
              <Form.Item name="description" label="描述" style={{ marginBottom: 0 }}>
                <TextArea rows={2} placeholder="这个专家团用来做什么..." />
              </Form.Item>
            </div>
          </div>
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
          <Form.Item name="maxRounds" label="最大讨论轮次" style={{ marginBottom: 0 }}>
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
                  const preset = PRESET_EXPERTS.find((p) => p.memberRole === value)
                  if (preset) handleAddPreset(preset)
                }}
                options={PRESET_EXPERTS.map((p) => ({
                  label: `${p.avatar} ${p.memberName}`,
                  value: p.memberRole,
                }))}
                allowClear
              />
              <Button icon={<UserAddOutlined />} onClick={openAddModal}>
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
            members.map((member, index) => {
              const roleColor = getExpertRoleColor(member.memberRole)
              return (
                <div
                  key={index}
                  className={`${styles.memberListCard} ${styles.memberListCardEditable} ${member.isEnabled === 0 ? styles.memberCardDisabled : ''}`}
                  style={{ borderLeft: `3px solid ${member.memberRole ? roleColor : '#d9d9d9'}` }}
                  onClick={() => openEditModal(index)}
                >
                  <div className={styles.memberListCardHeader}>
                    <div
                      className={styles.memberAvatar}
                      style={{ backgroundColor: roleColor + '18', color: roleColor }}
                    >
                      {member.avatar || '🤖'}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Space>
                        <Text strong>{member.memberName || `专家 #${index + 1}`}</Text>
                        {member.memberRole && (
                          <Text type="secondary">({member.memberRole})</Text>
                        )}
                        {!member.isEnabled && <span style={{ fontSize: 12, color: '#999' }}>已禁用</span>}
                      </Space>
                    </div>
                    <Space size={4} onClick={(e) => e.stopPropagation()}>
                      <Button
                        type="text"
                        icon={<EditOutlined />}
                        size="small"
                        onClick={() => openEditModal(index)}
                      />
                      <Popconfirm
                        title="确定移除此专家？"
                        onConfirm={() => handleRemoveMember(index)}
                      >
                        <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                      </Popconfirm>
                    </Space>
                  </div>
                  <p className={styles.memberPrompt}>
                    {member.systemPrompt || '暂无提示词，点击编辑添加...'}
                  </p>
                  <div className={styles.memberMeta}>
                    <span>模型: {member.modelName || '默认'}</span>
                    <span>温度: {member.temperature.toFixed(1)}</span>
                    <span>Tokens: {member.maxTokens}</span>
                  </div>
                </div>
              )
            })
          )}
        </Card>
      </Form>

      {/* 底部操作栏 */}
      <div className={styles.editorFooter}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={onCancel}>取消</Button>
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

      {/* 成员编辑弹窗 */}
      <MemberEditModal
        open={modalOpen}
        member={editingMember}
        isNew={isNewMember}
        onOk={handleModalOk}
        onCancel={handleModalCancel}
      />
    </div>
  )
}
