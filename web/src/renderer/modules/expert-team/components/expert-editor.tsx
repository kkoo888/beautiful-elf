/** 专家创建/编辑弹窗 */

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
} from 'antd'
import { ThunderboltOutlined, PictureOutlined } from '@ant-design/icons'
import { CompactModelSelect } from '@/modules/shared/components/model-selector'
import { ImageCropModal } from '@/modules/image-gallery/components/image-crop-modal'
import type { ExpertFormInput } from '../types'
import { getExpertRoleColor } from '../types'
import { polishPrompt } from '../services/expert-team-api'
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

/** 预设专家角色 */
const PRESET_ROLES = [
  '架构师', '测试专家', '产品经理', '安全专家', '数据专家',
  '前端工程师', '后端工程师', 'DevOps工程师', 'UI设计师', '技术顾问',
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

interface ExpertEditorModalProps {
  open: boolean
  expert: ExpertFormInput | null
  isNew: boolean
  onOk: (data: ExpertFormInput) => void
  onCancel: () => void
}

/** 专家编辑弹窗 */
export function ExpertEditorModal({
  open,
  expert,
  isNew,
  onOk,
  onCancel,
}: ExpertEditorModalProps) {
  const [form] = Form.useForm()
  const [avatar, setAvatar] = useState(expert?.avatar ?? '🤖')
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const [showImagePicker, setShowImagePicker] = useState(false)
  const [isCustomRole, setIsCustomRole] = useState(false)
  const [polishing, setPolishing] = useState(false)

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
      setIsCustomRole(false)
      form.setFieldsValue({
        memberName: '',
        memberRole: undefined,
        customRole: '',
        systemPrompt: '',
        modelName: '',
        temperature: 0.7,
        maxTokens: 2048,
        isEnabled: true,
      })
    }
  }, [open, expert, isNew, form])

  const handleOk = useCallback(async () => {
    try {
      const values = await form.validateFields()
      const memberRole = values.memberRole === '自定义' ? values.customRole : values.memberRole
      onOk({
        memberName: values.memberName,
        memberRole,
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

  const handlePolish = useCallback(async () => {
    const content = form.getFieldValue('systemPrompt')
    if (!content?.trim()) {
      return
    }
    setPolishing(true)
    try {
      const polished = await polishPrompt(content)
      form.setFieldValue('systemPrompt', polished)
    } catch {
      // polish failed silently
    } finally {
      setPolishing(false)
    }
  }, [form])

  const roleColor = expert ? getExpertRoleColor(expert.memberRole) : '#d9d9d9'

  const isImageAvatar = avatar && avatar.startsWith('data:image')

  return (
    <Modal
      open={open}
      title={isNew ? '新建专家' : '编辑专家'}
      onOk={handleOk}
      onCancel={onCancel}
      width={600}
      okText="确定"
      cancelText="取消"
    >
      {/* 头像区域 */}
      <div className={styles.modalAvatarWrap}>
        <div
          className={styles.modalAvatarLarge}
          style={{
            backgroundColor: isImageAvatar ? 'transparent' : roleColor + '18',
            color: isImageAvatar ? 'transparent' : roleColor,
            overflow: 'hidden',
          }}
          onClick={() => setShowEmojiPicker(!showEmojiPicker)}
        >
          {isImageAvatar ? (
            <img src={avatar} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          ) : (
            avatar
          )}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 16 }}>
            {expert?.memberName || '新专家'}
          </div>
          <Text type="secondary" style={{ fontSize: 13 }}>
            {expert?.memberRole || '点击头像更换'}
          </Text>
        </div>
      </div>

      {/* 头像选择按钮组 */}
      <div style={{ marginBottom: 16 }}>
        <Space size={8}>
          <Button
            size="small"
            icon={<span style={{ fontSize: 14 }}>😊</span>}
            onClick={() => { setShowEmojiPicker(!showEmojiPicker); setShowImagePicker(false) }}
          >
            Emoji
          </Button>
          <Button
            size="small"
            icon={<PictureOutlined />}
            onClick={() => { setShowImagePicker(true); setShowEmojiPicker(false) }}
          >
            图片
          </Button>
        </Space>
      </div>

      {showEmojiPicker && (
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
            选择 Emoji 头像
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

      {/* 图片裁剪弹窗 */}
      <ImageCropModal
        open={showImagePicker}
        onOk={(base64) => {
          setAvatar(base64)
          setShowImagePicker(false)
        }}
        onCancel={() => setShowImagePicker(false)}
      />

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
            rules={[{ required: true, message: '请选择角色' }]}
            style={{ flex: 1 }}
          >
            <Select
              placeholder="选择角色"
              onChange={(val) => setIsCustomRole(val === '自定义')}
              options={[
                ...PRESET_ROLES.map((r) => ({ label: r, value: r })),
                { label: '自定义', value: '自定义' },
              ]}
            />
          </Form.Item>
        </div>

        {isCustomRole && (
          <Form.Item
            name="customRole"
            label="自定义角色"
            rules={[{ required: true, message: '请输入自定义角色' }]}
          >
            <Input placeholder="如: 技术顾问" />
          </Form.Item>
        )}

        <Form.Item
          name="systemPrompt"
          label={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <span>系统提示词</span>
              <Button
                type="link"
                size="small"
                icon={<ThunderboltOutlined />}
                loading={polishing}
                onClick={handlePolish}
                style={{ padding: 0, fontSize: 12 }}
              >
                润色内容
              </Button>
            </div>
          }
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
