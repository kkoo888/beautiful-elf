/**
 * 灵魂引导组件
 * 用 Ant Design Steps 引导用户创建助手人格
 * 3 步流程：基本信息 → 性格选择 → 完成预览
 */

import { useCallback, useMemo, useState } from 'react'
import {
  Steps,
  Button,
  Input,
  Select,
  Slider,
  Tag,
  Typography,
  Upload,
  Space
} from 'antd'
import {
  UserOutlined,
  SmileOutlined,
  RocketOutlined,
  CameraOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  CheckOutlined,
  SkipOutlined
} from '@ant-design/icons'
import {
  PERSONALITY_PRESETS,
  SPEAKING_STYLES
} from '../types/settings'
import type { SoulOnboardData, SoulOnboardProps } from '../types/soul-onboard'
import styles from './settings-panel.module.css'

const { Text, Title, Paragraph } = Typography
const { TextArea } = Input

const INITIAL_DATA: SoulOnboardData = {
  step: 0,
  name: '',
  avatar: '',
  personality: [],
  speakingStyle: '温柔亲切',
  emotionalTendency: 60,
  backgroundStory: ''
}

const STEP_ITEMS = [
  { title: '基本信息', icon: <UserOutlined /> },
  { title: '性格塑造', icon: <SmileOutlined /> },
  { title: '完成', icon: <RocketOutlined /> }
]

export function SoulOnboard({ onComplete, onSkip }: SoulOnboardProps) {
  const [data, setData] = useState<SoulOnboardData>(INITIAL_DATA)

  const update = useCallback(
    (patch: Partial<SoulOnboardData>) => setData((prev) => ({ ...prev, ...patch })),
    []
  )

  const canNext = useMemo(() => {
    if (data.step === 0) return data.name.trim().length > 0
    return true
  }, [data.step, data.name])

  const handleNext = useCallback(() => {
    if (data.step < 2) {
      update({ step: data.step + 1 })
    } else {
      onComplete(data)
    }
  }, [data, update, onComplete])

  const handlePrev = useCallback(() => {
    if (data.step > 0) update({ step: data.step - 1 })
  }, [data.step, update])

  const togglePersonality = useCallback(
    (label: string) => {
      const current = data.personality
      const next = current.includes(label)
        ? current.filter((p) => p !== label)
        : [...current, label]
      update({ personality: next })
    },
    [data.personality, update]
  )

  /** 实时预览描述 */
  const previewDesc = useMemo(() => {
    const parts: string[] = []
    if (data.name) parts.push(`我是${data.name}`)
    if (data.personality.length > 0) {
      parts.push(`，一个${data.personality.join('又')}的助手`)
    }
    if (data.speakingStyle) parts.push(`，说话风格${data.speakingStyle}`)
    if (data.emotionalTendency >= 70) {
      parts.push('，我很感性、富有同理心 ❤️')
    } else if (data.emotionalTendency >= 40) {
      parts.push('，我理性与感性兼备 🤝')
    } else {
      parts.push('，我偏理性客观 🧊')
    }
    if (data.backgroundStory) parts.push(`\n\n📖 ${data.backgroundStory}`)
    return parts.join('')
  }, [data])

  /** 渲染当前步骤内容 */
  const renderStep = () => {
    switch (data.step) {
      case 0:
        return (
          <div className={styles.onboardStep}>
            <Title level={5}>👋 给你的助手起个名字吧</Title>

            {/* 头像 */}
            <div className={styles.avatarUpload}>
              <div className={styles.avatarPreview}>
                {data.avatar ? (
                  <img src={data.avatar} alt="avatar" />
                ) : (
                  <UserOutlined style={{ color: '#bfbfbf', fontSize: 36 }} />
                )}
              </div>
              <Upload
                showUploadList={false}
                beforeUpload={(file) => {
                  const reader = new FileReader()
                  reader.onload = (e) => update({ avatar: e.target?.result as string })
                  reader.readAsDataURL(file)
                  return false
                }}
                accept="image/*"
              >
                <Tag icon={<CameraOutlined />} color="pink" style={{ cursor: 'pointer' }}>
                  上传头像
                </Tag>
              </Upload>
            </div>

            {/* 名称 */}
            <div>
              <Text className={styles.formLabel}>助手名称</Text>
              <Input
                value={data.name}
                onChange={(e) => update({ name: e.target.value })}
                placeholder="例如：小茜、艾露、Momo..."
                maxLength={20}
                showCount
                size="large"
                style={{ maxWidth: 400 }}
              />
            </div>
          </div>
        )

      case 1:
        return (
          <div className={styles.onboardStep}>
            <Title level={5}>🎨 塑造你的助手性格</Title>

            {/* 性格标签 */}
            <div>
              <Text className={styles.formLabel}>选择性格标签（可多选）</Text>
              <div className={styles.personalityTags}>
                {PERSONALITY_PRESETS.map((preset) => {
                  const selected = data.personality.includes(preset.label)
                  return (
                    <Tag
                      key={preset.label}
                      className={styles.personalityTag}
                      color={selected ? preset.color : 'default'}
                      style={{
                        opacity: selected ? 1 : 0.6,
                        transform: selected ? 'scale(1.05)' : 'scale(1)'
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
            <div>
              <Text className={styles.formLabel}>说话风格</Text>
              <Select
                value={data.speakingStyle}
                onChange={(val) => update({ speakingStyle: val })}
                options={SPEAKING_STYLES.map((s) => ({ label: s, value: s }))}
                style={{ width: 200 }}
              />
            </div>

            {/* 情感倾向 */}
            <div>
              <Text className={styles.formLabel}>情感倾向</Text>
              <div className={styles.emotionSlider}>
                <Slider
                  min={0}
                  max={100}
                  value={data.emotionalTendency}
                  onChange={(val) => update({ emotionalTendency: val })}
                  styles={{ track: { background: 'linear-gradient(90deg, #597ef7, #ff85c0)' } }}
                />
                <div className={styles.emotionLabels}>
                  <span>🧊 理性客观</span>
                  <span>💖 感性共情</span>
                </div>
              </div>
            </div>

            {/* 背景故事 */}
            <div>
              <Text className={styles.formLabel}>背景故事（选填）</Text>
              <TextArea
                value={data.backgroundStory}
                onChange={(e) => update({ backgroundStory: e.target.value })}
                placeholder="给你的助手写一段背景故事，让它更有灵魂..."
                rows={3}
                maxLength={500}
                showCount
              />
            </div>
          </div>
        )

      case 2:
        return (
          <div className={styles.onboardStep}>
            <Title level={5}>🎉 太棒了！来认识一下你的助手吧</Title>

            <div className={styles.soulPreview}>
              <div style={{ textAlign: 'center', marginBottom: 16 }}>
                <div className={styles.avatarPreview} style={{ margin: '0 auto 12px', width: 96, height: 96 }}>
                  {data.avatar ? (
                    <img src={data.avatar} alt="avatar" />
                  ) : (
                    <UserOutlined style={{ color: '#bfbfbf', fontSize: 48 }} />
                  )}
                </div>
                <Title level={4} style={{ marginBottom: 4 }}>{data.name}</Title>
                <Space>
                  {data.personality.map((p) => {
                    const preset = PERSONALITY_PRESETS.find((pp) => pp.label === p)
                    return (
                      <Tag key={p} color={preset?.color || 'default'}>
                        {p}
                      </Tag>
                    )
                  })}
                </Space>
              </div>
              <div className={styles.soulPreviewDesc}>{previewDesc}</div>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className={styles.onboardContainer}>
      <Steps
        current={data.step}
        items={STEP_ITEMS}
        style={{ marginBottom: 32 }}
      />

      {renderStep()}

      <div className={styles.onboardNav}>
        <div>
          {data.step > 0 && (
            <Button icon={<ArrowLeftOutlined />} onClick={handlePrev}>
              上一步
            </Button>
          )}
        </div>
        <Space>
          {onSkip && data.step < 2 && (
            <Button type="text" icon={<SkipOutlined />} onClick={onSkip}>
              跳过
            </Button>
          )}
          <Button
            type="primary"
            disabled={!canNext}
            icon={data.step === 2 ? <CheckOutlined /> : <ArrowRightOutlined />}
            onClick={handleNext}
          >
            {data.step === 2 ? '开始使用' : '下一步'}
          </Button>
        </Space>
      </div>
    </div>
  )
}
