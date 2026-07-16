/**
 * 灵魂配置组件
 * 名称、头像、性格标签、说话风格、情感倾向、背景故事、实时预览
 */

import { useCallback, useMemo, useRef, useState } from 'react'
import { Input, Select, Slider, Typography, Tag, Upload, App } from 'antd'
import { UserOutlined, CameraOutlined } from '@ant-design/icons'
import type { SoulConfig } from '../types/settings'
import { PERSONALITY_PRESETS, SPEAKING_STYLES } from '../types/settings'
import { uploadAvatar } from '../services/settings-api'
import { toAvatarUrl } from '../utils/avatar'
import styles from './settings-panel.module.css'

const { Text } = Typography
const { TextArea } = Input

interface SoulSettingsProps {
  soul: SoulConfig
  onChange: (partial: Partial<SoulConfig>) => void
}

export function SoulSettings({ soul, onChange }: SoulSettingsProps) {
  const { message } = App.useApp()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isUploading, setIsUploading] = useState(false)

  /** 切换性格标签 */
  const togglePersonality = useCallback(
    (label: string) => {
      const current = soul.personality
      const next = current.includes(label)
        ? current.filter((p) => p !== label)
        : [...current, label]
      onChange({ personality: next })
    },
    [soul.personality, onChange]
  )

  /** 处理头像上传 */
  const handleAvatarUpload = useCallback(
    async (file: File) => {
      // 验证文件类型
      if (!file.type.startsWith('image/')) {
        message.error('请上传图片文件')
        return false
      }
      
      // 验证文件大小（最大 2MB）
      if (file.size > 2 * 1024 * 1024) {
        message.error('头像文件最大 2MB')
        return false
      }
      
      setIsUploading(true)
      try {
        const formData = new FormData()
        formData.append('file', file)
        const result = await uploadAvatar(formData)
        onChange({ avatar: result.path })
        message.success('头像上传成功')
      } catch (error) {
        message.error('头像上传失败，请重试')
        console.error('头像上传失败:', error)
      } finally {
        setIsUploading(false)
      }
      return false
    },
    [onChange, message]
  )

  /** 实时人格描述预览 */
  const previewDesc = useMemo(() => {
    const parts: string[] = []
    if (soul.name) parts.push(`${soul.name}是一个`)
    if (soul.personality.length > 0) {
      parts.push(soul.personality.join('又'))
    }
    if (soul.speakingStyle) parts.push(`的助手，说话风格${soul.speakingStyle}`)
    if (soul.emotionalTendency >= 70) {
      parts.push('，情感丰富、富有同理心')
    } else if (soul.emotionalTendency >= 40) {
      parts.push('，理性与感性兼备')
    } else {
      parts.push('，偏理性客观')
    }
    if (soul.backgroundStory) parts.push(`。${soul.backgroundStory}`)
    return parts.join('')
  }, [soul])

  return (
    <div className={styles.soulSection}>
      {/* 头像上传 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>头像</Text>
        <div className={styles.avatarUpload}>
          <div className={styles.avatarPreview} onClick={() => fileInputRef.current?.click()}>
            {soul.avatar ? (
              <img src={toAvatarUrl(soul.avatar)} alt="avatar" />
            ) : (
              <UserOutlined style={{ color: '#bfbfbf' }} />
            )}
          </div>
          <div>
            <Upload
              showUploadList={false}
              beforeUpload={(file) => {
                handleAvatarUpload(file)
                return false
              }}
              accept="image/*"
              disabled={isUploading}
            >
              <Tag icon={<CameraOutlined />} color="pink" style={{ cursor: isUploading ? 'not-allowed' : 'pointer' }}>
                {isUploading ? '上传中...' : '上传头像'}
              </Tag>
            </Upload>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleAvatarUpload(file)
              }}
            />
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
              支持 JPG、PNG 格式，最大 2MB
            </Text>
          </div>
        </div>
      </div>

      {/* 名称 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>助手名称</Text>
        <Input
          value={soul.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="给你的助手起个名字"
          maxLength={20}
          showCount
          style={{ maxWidth: 300 }}
        />
      </div>

      {/* 性格标签 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>性格标签（可多选）</Text>
        <div className={styles.personalityTags}>
          {PERSONALITY_PRESETS.map((preset) => {
            const selected = soul.personality.includes(preset.label)
            return (
              <Tag
                key={preset.label}
                className={styles.personalityTag}
                color={selected ? preset.color : 'default'}
                style={{
                  opacity: selected ? 1 : 0.6,
                  transform: selected ? 'scale(1.05)' : 'scale(1)',
                }}
                onClick={() => togglePersonality(preset.label)}
              >
                {selected ? '✓ ' : ''}
                {preset.label}
              </Tag>
            )
          })}
        </div>
      </div>

      {/* 说话风格 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>说话风格</Text>
        <Select
          value={soul.speakingStyle}
          onChange={(val) => onChange({ speakingStyle: val })}
          options={SPEAKING_STYLES.map((s) => ({ label: s, value: s }))}
          style={{ width: 200 }}
          placeholder="选择说话风格"
        />
      </div>

      {/* 情感倾向 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>情感倾向</Text>
        <div className={styles.emotionSlider}>
          <Slider
            min={0}
            max={100}
            value={soul.emotionalTendency}
            onChange={(val) => onChange({ emotionalTendency: val })}
            styles={{ track: { background: 'linear-gradient(90deg, #597ef7, #ff85c0)' } }}
          />
          <div className={styles.emotionLabels}>
            <span>🧊 理性客观</span>
            <span>💖 感性共情</span>
          </div>
        </div>
      </div>

      {/* 背景故事 */}
      <div className={styles.formItem}>
        <Text className={styles.formLabel}>背景故事（选填）</Text>
        <TextArea
          value={soul.backgroundStory}
          onChange={(e) => onChange({ backgroundStory: e.target.value })}
          placeholder="给你的助手写一段背景故事，让它更有趣..."
          rows={3}
          maxLength={500}
          showCount
        />
      </div>

      {/* 实时预览 */}
      {soul.name && (
        <div className={styles.soulPreview}>
          <div className={styles.soulPreviewTitle}>✨ 人格预览</div>
          <div className={styles.soulPreviewDesc}>{previewDesc}</div>
        </div>
      )}
    </div>
  )
}
