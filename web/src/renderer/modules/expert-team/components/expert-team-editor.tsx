/** 专家团编辑器组件 — 管理基本信息 + 绑定已有专家 */

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
  Popconfirm,
  Tag,
  App,
} from 'antd'
import {
  DeleteOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  UserAddOutlined,
  TeamOutlined,
  PictureOutlined,
} from '@ant-design/icons'
import type { ExpertTeam, ExpertTeamFormInput, Expert } from '../types'
import { getExpertRoleColor } from '../types'
import { TeamBindExpertsModal } from './team-bind-experts-modal'
import { ImageCropModal } from '@/modules/image-gallery/components/image-crop-modal'
import styles from './expert-team.module.css'

const { TextArea } = Input
const { Text } = Typography

/** 专家团图标列表 */
const TEAM_ICONS = [
  '👥', '🧠', '🏗️', '🔬', '🎯', '💡', '🚀', '⚡',
  '🌐', '📊', '🛡️', '🎨', '🤖', '🔧', '⚙️', '📋',
]

/** Emoji 网格选择器 */
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

interface ExpertTeamEditorProps {
  team?: ExpertTeam
  /** 所有可用专家 */
  allExperts: Expert[]
  onSave: (input: ExpertTeamFormInput) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export function ExpertTeamEditor({ team, allExperts, onSave, onCancel, loading }: ExpertTeamEditorProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [teamIcon, setTeamIcon] = useState(team?.icon ?? '👥')
  const [showTeamIconPicker, setShowTeamIconPicker] = useState(false)
  const [showTeamImagePicker, setShowTeamImagePicker] = useState(false)

  // 已绑定专家 ID 列表
  const [expertIds, setExpertIds] = useState<number[]>(
    team?.experts.map((e) => e.id) ?? []
  )

  // 组长 ID
  const [leaderId, setLeaderId] = useState<number>(team?.leaderId ?? 0)

  // 绑定弹窗
  const [bindModalOpen, setBindModalOpen] = useState(false)

  // 已绑定专家完整数据
  const boundExperts = allExperts.filter((e) => expertIds.includes(e.id))

  const handleBindConfirm = useCallback((ids: number[]) => {
    setExpertIds(ids)
    setBindModalOpen(false)
  }, [])

  const handleRemoveExpert = useCallback((id: number) => {
    setExpertIds((prev) => prev.filter((i) => i !== id))
  }, [])

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields()

      if (expertIds.length === 0) {
        message.warning('请至少绑定一位专家')
        return
      }

      const input: ExpertTeamFormInput = {
        teamName: values.teamName,
        description: values.description ?? '',
        icon: teamIcon,
        category: values.category ?? '通用',
        leaderId: leaderId || undefined,
        orchestratorPrompt: values.orchestratorPrompt ?? '',
        synthesizerPrompt: values.synthesizerPrompt ?? '',
        maxRounds: values.maxRounds ?? 3,
        expertIds,
      }

      await onSave(input)
    } catch {
      // form validation failed
    }
  }, [form, expertIds, leaderId, teamIcon, onSave, message])

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
                style={{
                  cursor: 'pointer',
                  overflow: 'hidden',
                  backgroundColor: teamIcon?.startsWith('data:image') ? 'transparent' : undefined,
                }}
                onClick={() => setShowTeamIconPicker(!showTeamIconPicker)}
              >
                {teamIcon?.startsWith('data:image') ? (
                  <img src={teamIcon} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  teamIcon
                )}
              </div>
              <Space size={4}>
                <Button size="small" onClick={() => setShowTeamIconPicker(!showTeamIconPicker)}>Emoji</Button>
                <Button size="small" icon={<PictureOutlined />} onClick={() => setShowTeamImagePicker(true)}>图片</Button>
              </Space>
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
              <ImageCropModal
                open={showTeamImagePicker}
                onOk={(base64) => {
                  setTeamIcon(base64)
                  setShowTeamImagePicker(false)
                }}
                onCancel={() => setShowTeamImagePicker(false)}
              />
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

        {/* 绑定专家 */}
        <Card
          title={
            <Space>
              <TeamOutlined />
              <span>绑定专家</span>
              <Text type="secondary">({boundExperts.length} 人)</Text>
            </Space>
          }
          extra={
            <Button icon={<UserAddOutlined />} onClick={() => setBindModalOpen(true)}>
              选择专家
            </Button>
          }
          style={{ marginTop: 16 }}
        >
          {/* 组长选择器 */}
          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>👑 组长（PM）</Text>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              组长负责分析任务、分配给专家、评估完成质量。从已绑定的专家中选择。
            </Text>
            <Select
              placeholder="选择组长..."
              value={leaderId || undefined}
              onChange={(v) => setLeaderId(v)}
              allowClear
              style={{ width: '100%' }}
              options={boundExperts.map((e) => ({
                label: `${e.avatar ?? '🤖'} ${e.memberName}（${e.memberRole}）`,
                value: e.id,
              }))}
            />
          </div>
          {boundExperts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Text type="secondary">暂未绑定专家，请点击上方按钮选择</Text>
            </div>
          ) : (
            boundExperts.map((expert) => {
              const roleColor = getExpertRoleColor(expert.memberRole)
              return (
                <div
                  key={expert.id}
                  className={styles.memberListCard}
                  style={{ borderLeft: `3px solid ${roleColor}` }}
                >
                  <div className={styles.memberListCardHeader}>
                    <div
                      className={styles.memberAvatar}
                      style={{
                        backgroundColor: expert.avatar?.startsWith('data:image') ? 'transparent' : roleColor + '18',
                        color: expert.avatar?.startsWith('data:image') ? 'transparent' : roleColor,
                        overflow: 'hidden',
                      }}
                    >
                      {expert.avatar?.startsWith('data:image') ? (
                        <img src={expert.avatar} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      ) : (
                        expert.avatar || '🤖'
                      )}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Space>
                        <Text strong>{expert.memberName}</Text>
                        <Tag color={roleColor} style={{ margin: 0 }}>{expert.memberRole}</Tag>
                        {!expert.isEnabled && <Tag color="default">已禁用</Tag>}
                      </Space>
                    </div>
                    <Popconfirm
                      title="确定移除此专家？"
                      onConfirm={() => handleRemoveExpert(expert.id)}
                    >
                      <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                    </Popconfirm>
                  </div>
                  <p className={styles.memberPrompt}>
                    {expert.systemPrompt || '暂无提示词'}
                  </p>
                  <div className={styles.memberMeta}>
                    <span>模型: {expert.modelName || '默认'}</span>
                    <span>温度: {expert.temperature.toFixed(1)}</span>
                    <span>Tokens: {expert.maxTokens}</span>
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

      {/* 绑定专家弹窗 */}
      <TeamBindExpertsModal
        open={bindModalOpen}
        experts={allExperts}
        boundIds={expertIds}
        onOk={handleBindConfirm}
        onCancel={() => setBindModalOpen(false)}
      />
    </div>
  )
}
