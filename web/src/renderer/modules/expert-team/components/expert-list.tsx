/** 独立专家列表组件 */

import { useState, useCallback } from 'react'
import {
  Card,
  Tag,
  Space,
  Button,
  Popconfirm,
  Typography,
  Spin,
  Tooltip,
  App,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { Expert, ExpertFormInput } from '../types'
import { getExpertRoleColor } from '../types'
import { ExpertEditorModal } from './expert-editor'
import { EmptyState } from '@/components/empty-state'
import styles from './expert-team.module.css'

const { Text } = Typography

/** 预设专家角色快速创建 */
const PRESET_EXPERTS: ExpertFormInput[] = [
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

interface ExpertListProps {
  experts: Expert[]
  loading?: boolean
  onCreate: (input: ExpertFormInput) => Promise<Expert>
  onUpdate: (id: number, input: Partial<ExpertFormInput>) => Promise<Expert>
  onDelete: (id: number) => Promise<void>
  onBindSkills?: (expertId: number) => void
}

export function ExpertList({
  experts,
  loading,
  onCreate,
  onUpdate,
  onDelete,
  onBindSkills,
}: ExpertListProps) {
  const { message } = App.useApp()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingExpert, setEditingExpert] = useState<{ expert: ExpertFormInput | null; id: number | null }>({
    expert: null,
    id: null,
  })
  const [isSaving, setIsSaving] = useState(false)

  const openCreateModal = useCallback(() => {
    setEditingExpert({ expert: null, id: null })
    setModalOpen(true)
  }, [])

  const openEditModal = useCallback((expert: Expert) => {
    setEditingExpert({
      expert: {
        memberName: expert.memberName,
        memberRole: expert.memberRole,
        avatar: expert.avatar,
        goal: expert.goal || '',
        backstory: expert.backstory || '',
        systemPrompt: expert.systemPrompt,
        modelName: expert.modelName,
        temperature: expert.temperature,
        maxTokens: expert.maxTokens,
        isDelegationAllowed: expert.isDelegationAllowed === 1,
        maxExecutionTime: expert.maxExecutionTime || 120,
        isEnabled: expert.isEnabled,
      },
      id: expert.id,
    })
    setModalOpen(true)
  }, [])

  const handleModalOk = useCallback(async (data: ExpertFormInput) => {
    setIsSaving(true)
    try {
      if (editingExpert.id) {
        await onUpdate(editingExpert.id, data)
        message.success('已更新')
      } else {
        await onCreate(data)
        message.success('已创建')
      }
      setModalOpen(false)
    } catch {
      message.error('操作失败')
    } finally {
      setIsSaving(false)
    }
  }, [editingExpert.id, onCreate, onUpdate, message])

  const handleModalCancel = useCallback(() => {
    setModalOpen(false)
  }, [])

  const handleDelete = useCallback(async (id: number) => {
    try {
      await onDelete(id)
      message.success('已删除')
    } catch {
      message.error('删除失败')
    }
  }, [onDelete, message])

  const handleQuickCreate = useCallback(async (preset: ExpertFormInput) => {
    if (experts.some((e) => e.memberRole === preset.memberRole)) {
      message.warning(`已存在「${preset.memberRole}」角色的专家`)
      return
    }
    try {
      await onCreate(preset)
      message.success(`已创建「${preset.memberName}」`)
    } catch {
      message.error('创建失败')
    }
  }, [experts, onCreate, message])

  if (loading && experts.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      {/* 操作栏 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
            快速添加预设专家：
          </Text>
          <Space wrap>
            {PRESET_EXPERTS.map((preset) => (
              <Tooltip key={preset.memberRole} title={`创建${preset.memberName}`}>
                <Button
                  size="small"
                  icon={<PlusOutlined />}
                  disabled={experts.some((e) => e.memberRole === preset.memberRole)}
                  onClick={() => handleQuickCreate(preset)}
                >
                  {preset.avatar} {preset.memberName}
                </Button>
              </Tooltip>
            ))}
          </Space>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          新建专家
        </Button>
      </div>

      {/* 专家卡片列表 */}
      {experts.length === 0 ? (
        <EmptyState
          description="还没有专家，点击上方预设或自定义创建吧"
          icon="🧑‍💼"
        />
      ) : (
        <div className={styles.cardGrid}>
          {experts.map((expert) => {
            const roleColor = getExpertRoleColor(expert.memberRole)
            return (
              <Card
                key={expert.id}
                className={styles.teamCard}
                hoverable
                styles={{ body: { padding: '20px' } }}
              >
                <div className={styles.teamCardHeader}>
                  <div
                    className={styles.teamCardAvatar}
                    style={{
                      backgroundColor: expert.avatar?.startsWith('data:image') ? 'transparent' : roleColor + '18',
                      color: expert.avatar?.startsWith('data:image') ? 'transparent' : roleColor,
                      overflow: 'hidden',
                    }}
                  >
                    {expert.avatar?.startsWith('data:image') ? (
                      <img src={expert.avatar} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      expert.avatar
                    )}
                  </div>
                  <div className={styles.teamCardInfo}>
                    <div className={styles.teamCardName}>{expert.memberName}</div>
                    <div className={styles.teamCardDesc}>{expert.memberRole}</div>
                  </div>
                  <Tag color={expert.isEnabled ? 'green' : 'default'}>
                    {expert.isEnabled ? '启用' : '禁用'}
                  </Tag>
                </div>

                <p className={styles.memberPrompt} style={{ margin: '8px 0' }}>
                  {expert.systemPrompt}
                </p>

                <div className={styles.memberMeta}>
                  <span>模型: {expert.modelName || '默认'}</span>
                  <span>温度: {expert.temperature.toFixed(1)}</span>
                  <span>Tokens: {expert.maxTokens}</span>
                </div>

                <div className={styles.teamCardActions} style={{ marginTop: 8 }}>
                  <Tooltip title="绑定技能">
                    <Button
                      type="text"
                      size="small"
                      icon={<ThunderboltOutlined />}
                      onClick={() => openEditModal(expert)}
                    />
                  </Tooltip>
                  <Tooltip title="编辑">
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => openEditModal(expert)}
                    />
                  </Tooltip>
                  <Popconfirm title="确定删除此专家？" onConfirm={() => handleDelete(expert.id)}>
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* 编辑弹窗 */}
      <ExpertEditorModal
        open={modalOpen}
        expert={editingExpert.expert}
        expertId={editingExpert.id}
        isNew={!editingExpert.id}
        onOk={handleModalOk}
        onCancel={handleModalCancel}
      />
    </div>
  )
}
