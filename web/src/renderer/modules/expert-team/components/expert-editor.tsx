/** 专家创建/编辑弹窗 — 左右分栏布局 */

import { useState, useCallback, useEffect } from 'react'
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Switch,
  Typography,
  Space,
  Tag,
  Empty,
  Spin,
  Divider,
  App,
} from 'antd'
import {
  ThunderboltOutlined,
  PictureOutlined,
  PlusOutlined,
  CloseCircleFilled,
} from '@ant-design/icons'
import { CompactModelSelect } from '@/modules/shared/components/model-selector'
import { ImageCropModal } from '@/modules/image-gallery/components/image-crop-modal'
import { ExpertAvatar } from '@/components/expert-avatar'
import type { ExpertFormInput, ExpertSkill } from '../types'
import { getExpertRoleColor } from '../types'
import { polishPrompt, fetchExpertSkills, bindExpertSkill, unbindExpertSkill } from '../services/expert-team-api'
import { fetchSkills } from '@/modules/skills/services/skills-api'
import type { Skill } from '@/modules/skills/types/skills'
import { ExpertBindSkillsModal } from './expert-bind-skills-modal'

const { TextArea } = Input
const { Text } = Typography

const PRESET_AVATARS = [
  '🤖', '👨‍💻', '👩‍💻', '🏗️', '🧪', '📋', '🛡️', '📊',
  '🎨', '🔬', '🎯', '💡', '🔍', '📝', '🧠', '👨‍🔬',
  '👩‍🔬', '👨‍🏫', '👩‍🏫', '🧙‍♂️', '🦾', '👁️', '🗣️', '🤝',
  '🎭', '⚖️', '📈', '🗄️', '🌐', '🔧', '⚙️', '🚀',
]

const PRESET_ROLES = [
  '架构师', '测试专家', '产品经理', '安全专家', '数据专家',
  '前端工程师', '后端工程师', 'DevOps工程师', 'UI设计师', '技术顾问',
]

function EmojiGrid({ value, options, onChange }: {
  value: string; options: string[]; onChange: (v: string) => void
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 4 }}>
      {options.map((emoji) => (
        <div
          key={emoji}
          style={{
            width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center',
            borderRadius: 6, cursor: 'pointer', fontSize: 18,
            background: value === emoji ? '#e6f7ff' : 'transparent',
            border: value === emoji ? '1.5px solid #1890ff' : '1.5px solid transparent',
            transition: 'all 0.15s',
          }}
          onClick={() => onChange(emoji)}
        >
          {emoji}
        </div>
      ))}
    </div>
  )
}

interface ExpertEditorModalProps {
  open: boolean
  expert: ExpertFormInput | null
  expertId?: number | null
  isNew: boolean
  onOk: (data: ExpertFormInput) => void
  onCancel: () => void
}

export function ExpertEditorModal({
  open, expert, expertId, isNew, onOk, onCancel,
}: ExpertEditorModalProps) {
  const [form] = Form.useForm()
  const { message } = App.useApp()
  const [avatar, setAvatar] = useState(expert?.avatar ?? '🤖')
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const [showImagePicker, setShowImagePicker] = useState(false)
  const [isCustomRole, setIsCustomRole] = useState(false)
  const [polishing, setPolishing] = useState(false)

  // 技能绑定
  const [allSkills, setAllSkills] = useState<Skill[]>([])
  const [boundSkills, setBoundSkills] = useState<ExpertSkill[]>([])
  const [skillsLoading, setSkillsLoading] = useState(false)
  const [bindModalOpen, setBindModalOpen] = useState(false)

  useEffect(() => {
    if (open && expert) {
      setAvatar(expert.avatar ?? '🤖')
      const isPreset = PRESET_ROLES.includes(expert.memberRole)
      setIsCustomRole(!isPreset && !!expert.memberRole)
      form.setFieldsValue({
        memberName: expert.memberName,
        memberRole: isPreset ? expert.memberRole : '自定义',
        customRole: isPreset ? '' : expert.memberRole,
        systemPrompt: expert.systemPrompt,
        modelName: expert.modelName || '',
        temperature: expert.temperature,
        maxTokens: expert.maxTokens,
        isEnabled: expert.isEnabled !== 0,
      })
    } else if (open && isNew) {
      setIsCustomRole(false); setBoundSkills([])
      form.setFieldsValue({
        memberName: '', memberRole: undefined, customRole: '',
        systemPrompt: '', modelName: '', temperature: 0.7, maxTokens: 2048, isEnabled: true,
      })
    }
  }, [open, expert, isNew, form])

  const handleOk = useCallback(async () => {
    try {
      const values = await form.validateFields()
      const memberRole = values.memberRole === '自定义' ? values.customRole : values.memberRole
      onOk({
        memberName: values.memberName, memberRole, avatar,
        systemPrompt: values.systemPrompt, modelName: values.modelName || undefined,
        temperature: values.temperature, maxTokens: values.maxTokens,
        isEnabled: values.isEnabled ? 1 : 0,
      })
    } catch { /* validation failed */ }
  }, [form, avatar, onOk])

  const handlePolish = useCallback(async () => {
    const content = form.getFieldValue('systemPrompt')
    if (!content?.trim()) return
    setPolishing(true)
    try { form.setFieldValue('systemPrompt', await polishPrompt(content)) }
    catch { /* */ }
    finally { setPolishing(false) }
  }, [form])

  const roleColor = expert ? getExpertRoleColor(expert.memberRole) : '#d9d9d9'
  const isImageAvatar = avatar && avatar.startsWith('data:image')

  // 加载技能（新建专家时不请求）
  useEffect(() => {
    if (!open || isNew) return
    const load = async () => {
      setSkillsLoading(true)
      try {
        const [skillsRes, boundRes] = await Promise.all([
          fetchSkills({ isEnabled: 1, pageSize: 500 }),
          expertId ? fetchExpertSkills(expertId) : Promise.resolve([]),
        ])
        setAllSkills(skillsRes.data || [])
        setBoundSkills(boundRes || [])
      } catch (err) {
        message.error('加载技能列表失败，请检查网络或刷新重试')
      } finally { setSkillsLoading(false) }
    }
    load()
  }, [open, expertId, isNew])

  const handleBindSkills = useCallback(async (skillIds: number[]) => {
    if (!expertId) return
    try {
      const currentIds = new Set(boundSkills.map((s) => s.skillId))
      const newIds = skillIds.filter((id) => !currentIds.has(id))
      const removeBinds = boundSkills.filter((s) => !skillIds.includes(s.skillId))
      await Promise.all([
        ...newIds.map((skillId) => bindExpertSkill(expertId, { skillId })),
        ...removeBinds.map((bind) => unbindExpertSkill(bind.id)),
      ])
      setBoundSkills(await fetchExpertSkills(expertId) || [])
      setBindModalOpen(false)
    } catch { /* */ }
  }, [expertId, boundSkills])

  // ── 左栏：专家表单 ──
  const leftPanel = (
    <div style={{ flex: 1, minWidth: 0, paddingRight: 24, overflow: 'auto' }}>
      {/* 头像 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
        <div
          style={{
            width: 56, height: 56, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 28, cursor: 'pointer', flexShrink: 0,
            background: isImageAvatar ? 'transparent' : roleColor + '15',
            color: isImageAvatar ? 'transparent' : roleColor,
            border: `2px solid ${roleColor}30`, overflow: 'hidden', transition: 'all 0.2s',
          }}
          onClick={() => setShowEmojiPicker(!showEmojiPicker)}
        >
          {isImageAvatar
            ? <img src={avatar} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : avatar
          }
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{expert?.memberName || '新专家'}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>{expert?.memberRole || '点击头像更换'}</Text>
          <div style={{ marginTop: 4 }}>
            <Space size={4}>
              <Button size="small" style={{ fontSize: 12, height: 24, padding: '0 8px' }}
                icon={<span style={{ fontSize: 12 }}>😊</span>}
                onClick={() => { setShowEmojiPicker(!showEmojiPicker); setShowImagePicker(false) }}
              >Emoji</Button>
              <Button size="small" style={{ fontSize: 12, height: 24, padding: '0 8px' }}
                icon={<PictureOutlined />}
                onClick={() => { setShowImagePicker(true); setShowEmojiPicker(false) }}
              >图片</Button>
            </Space>
          </div>
        </div>
      </div>

      {showEmojiPicker && (
        <div style={{ marginBottom: 16, padding: '10px 12px', background: '#fafafa', borderRadius: 8 }}>
          <EmojiGrid value={avatar} options={PRESET_AVATARS} onChange={(v) => { setAvatar(v); setShowEmojiPicker(false) }} />
        </div>
      )}

      <ImageCropModal open={showImagePicker} onOk={(b64) => { setAvatar(b64); setShowImagePicker(false) }} onCancel={() => setShowImagePicker(false)} />

      {/* 表单 */}
      <Form form={form} layout="vertical" size="small">
        <div style={{ display: 'flex', gap: 10 }}>
          <Form.Item name="memberName" label="名称" rules={[{ required: true }]} style={{ flex: 1 }}>
            <Input placeholder="专家名称" />
          </Form.Item>
          <Form.Item name="memberRole" label="角色" rules={[{ required: true }]} style={{ flex: 1 }}>
            <Select placeholder="选择角色" onChange={(v) => setIsCustomRole(v === '自定义')}
              options={[...PRESET_ROLES.map((r) => ({ label: r, value: r })), { label: '自定义', value: '自定义' }]}
            />
          </Form.Item>
        </div>

        {isCustomRole && (
          <Form.Item name="customRole" label="自定义角色" rules={[{ required: true }]}>
            <Input placeholder="如: 技术顾问" />
          </Form.Item>
        )}

        <Form.Item name="systemPrompt" label={
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
            <span>系统提示词</span>
            <Button type="link" size="small" icon={<ThunderboltOutlined />} loading={polishing}
              onClick={handlePolish} style={{ padding: 0, fontSize: 12, height: 18 }}
            >润色</Button>
          </div>
        } rules={[{ required: true }]}>
          <TextArea rows={4} placeholder="定义这个专家的专业领域和行为方式..." />
        </Form.Item>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Form.Item label="模型" style={{ flex: 1, minWidth: 180 }}>
            <CompactModelSelect value={form.getFieldValue('modelName') || ''}
              onChange={(_v, _p, m) => form.setFieldValue('modelName', m)} placeholder="默认模型" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="温度" name="temperature" initialValue={0.7}>
            <InputNumber min={0} max={2} step={0.1} style={{ width: 80 }} />
          </Form.Item>
          <Form.Item label="Max Tokens" name="maxTokens" initialValue={2048}>
            <InputNumber min={1} max={8192} style={{ width: 100 }} />
          </Form.Item>
        </div>

        <Form.Item name="isEnabled" label="启用" valuePropName="checked" initialValue={true} style={{ marginBottom: 0 }}>
          <Switch size="small" />
        </Form.Item>
      </Form>
    </div>
  )

  // ── 右栏：技能绑定（新建专家时隐藏）──
  const rightPanel = isNew ? null : expertId ? (
    <div style={{ width: 260, flexShrink: 0, borderLeft: '1px solid #f0f0f0', paddingLeft: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <Text strong style={{ fontSize: 13 }}>
          <ThunderboltOutlined style={{ color: '#1890ff', marginRight: 5 }} />
          技能
        </Text>
        <Button type="link" size="small" icon={<PlusOutlined />}
          onClick={() => setBindModalOpen(true)} style={{ padding: 0, fontSize: 12 }}
        >
          {boundSkills.length > 0 ? '管理' : '添加'}
        </Button>
      </div>

      {skillsLoading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}><Spin size="small" /></div>
      ) : boundSkills.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={<Text type="secondary" style={{ fontSize: 12 }}>暂未绑定技能</Text>}
          style={{ margin: '40px 0' }}
        >
          <Button size="small" type="primary" ghost onClick={() => setBindModalOpen(true)}>
            <PlusOutlined /> 添加技能
          </Button>
        </Empty>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {boundSkills.map((bind) => {
            const skill = allSkills.find((s) => s.id === bind.skillId)
            const name = bind.skillDisplayName || skill?.displayName || skill?.name || `技能#${bind.skillId}`
            return (
              <div key={bind.id} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 10px', borderRadius: 8,
                background: '#f8f9fa', border: '1px solid #f0f0f0',
                transition: 'all 0.15s',
              }}>
                <ThunderboltOutlined style={{ color: '#1890ff', fontSize: 13, flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {name}
                  </div>
                  {skill?.description && (
                    <div style={{ fontSize: 11, color: '#8c8c8c', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {skill.description}
                    </div>
                  )}
                </div>
                <CloseCircleFilled
                  style={{ color: '#bbb', fontSize: 14, cursor: 'pointer', flexShrink: 0 }}
                  onClick={async () => {
                    await unbindExpertSkill(bind.id)
                    setBoundSkills((prev) => prev.filter((b) => b.id !== bind.id))
                  }}
                />
              </div>
            )
          })}
        </div>
      )}
    </div>
  ) : (
    <div style={{ width: 260, flexShrink: 0, borderLeft: '1px solid #f0f0f0', paddingLeft: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={<Text type="secondary" style={{ fontSize: 12 }}>保存后可绑定技能</Text>}
      />
    </div>
  )

  return (
    <>
      <Modal
        open={open}
        title={isNew ? '新建专家' : '编辑专家'}
        onOk={handleOk}
        onCancel={onCancel}
        width="80vw"
        okText="确定"
        cancelText="取消"
        styles={{ body: { padding: '20px 24px', display: 'flex', gap: 0, minHeight: 460, maxHeight: '70vh' } }}
      >
        {leftPanel}
        {rightPanel}
      </Modal>

      <ExpertBindSkillsModal
        open={bindModalOpen}
        skills={allSkills}
        boundSkills={boundSkills}
        loading={skillsLoading}
        onOk={handleBindSkills}
        onCancel={() => setBindModalOpen(false)}
      />
    </>
  )
}
