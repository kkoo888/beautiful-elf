/** 新增视频弹窗 — 三栏布局 */
import { useState, useCallback, useEffect } from 'react'
import {
  Modal, Form, Input, Select, Button, Space, Tag, App, InputNumber,
} from 'antd'
import { ThunderboltOutlined, PlusOutlined, HourglassOutlined, VideoCameraOutlined } from '@ant-design/icons'
import { CompactModelSelect, getProvidersCached } from '@/modules/shared/components/model-selector'
import { polishPrompt } from '@/modules/expert-team/services/expert-team-api'
import { fetchVideoTags, generateVideoPrompt } from '../services/video-gallery-api'
import type { VideoGalleryFormInput, VideoGenerateInput } from '../types'
import styles from './video-gallery.module.css'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'

const { TextArea } = Input

function toVideoUrl(filePath: string) {
  if (!filePath) return ''
  const filename = filePath.split(/[/\\]/).pop() || ''
  return `${API_BASE_URL}${API_PREFIX}/video_gallery/files/${encodeURIComponent(filename)}`
}

/** 预设尺寸选项 */
const SIZE_OPTIONS = [
  { label: '720p 横 1280 x 720 (16:9)', value: '1280x720' },
  { label: '720p 竖 720 x 1280 (9:16)', value: '720x1280' },
  { label: '720p 方 720 x 720 (1:1)', value: '720x720' },
  { label: '推荐 1152 x 768 (标准)', value: '1152x768' },
  { label: '1080p 横 1920 x 1080 (16:9)', value: '1920x1080' },
  { label: '1080p 竖 1080 x 1920 (9:16)', value: '1080x1920' },
  { label: '1080p 方 1080 x 1080 (1:1)', value: '1080x1080' },
  { label: '──────────── 自定义 ────────────', value: '__sep', disabled: true },
  { label: '自定义', value: 'custom' },
]

/** 帧数选项（8n+1） */
const FRAME_OPTIONS = [
  { label: '41 帧 (~1.7s)', value: 41 },
  { label: '81 帧 (~3.4s)', value: 81 },
  { label: '121 帧 (~5.0s)', value: 121 },
  { label: '161 帧 (~6.7s)', value: 161 },
  { label: '201 帧 (~8.4s)', value: 201 },
  { label: '241 帧 (~10.0s)', value: 241 },
  { label: '281 帧 (~11.7s)', value: 281 },
  { label: '321 帧 (~13.4s)', value: 321 },
  { label: '361 帧 (~15.0s)', value: 361 },
  { label: '401 帧 (~16.7s)', value: 401 },
  { label: '441 帧 (~18.4s)', value: 441 },
]

interface VideoCreateModalProps {
  open: boolean
  onOk: (input: VideoGalleryFormInput) => void
  onGenerate: (input: VideoGenerateInput) => Promise<{ name: string; filePath: string; thumbnailPath: string; width: number; height: number; numFrames: number; frameRate: number; duration: number }>
  isGenerating: boolean
  onCancel: () => void
}

export function VideoCreateModal({
  open,
  onOk,
  onGenerate,
  isGenerating,
  onCancel,
}: VideoCreateModalProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [generatedResult, setGeneratedResult] = useState<{
    name: string; filePath: string; thumbnailPath: string
  } | null>(null)
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [existingTags, setExistingTags] = useState<string[]>([])
  const [polishing, setPolishing] = useState(false)
  const [generatingPrompt, setGeneratingPrompt] = useState(false)
  const [sizeMode, setSizeMode] = useState('1152x768')
  const [customWidth, setCustomWidth] = useState(1152)
  const [customHeight, setCustomHeight] = useState(768)
  const [numFrames, setNumFrames] = useState(121)
  const [frameRate, setFrameRate] = useState(24)
  const [selectedModel, setSelectedModel] = useState('')

  useEffect(() => {
    if (open) {
      setTags([])
      setSelectedModel('')
      setGeneratedResult(null)
      fetchVideoTags().then((t) => setExistingTags(t)).catch(() => {})
      getProvidersCached().then((providers) => {
        for (const p of providers) {
          const m = p.models?.find((m) => m.modelName === 'agnes-video-v2.0')
          if (m) {
            setSelectedModel(`${p.id}:agnes-video-v2.0`)
            form.setFieldsValue({ modelName: 'agnes-video-v2.0', providerId: p.id })
            return
          }
        }
        if (providers.length > 0 && providers[0].models?.length) {
          const first = providers[0]
          setSelectedModel(`${first.id}:${first.models[0].modelName}`)
          form.setFieldsValue({ modelName: first.models[0].modelName, providerId: first.id })
        }
      }).catch(() => {})
    }
  }, [open, form])

  const handleGenerate = useCallback(async () => {
    try {
      const values = await form.validateFields(['prompt', 'negativePrompt', 'modelName', 'providerId'])
      const [w, h] = sizeMode === 'custom'
        ? [customWidth, customHeight]
        : sizeMode.split('x').map(Number)
      const result = await onGenerate({
        prompt: values.prompt,
        negativePrompt: values.negativePrompt || '',
        modelName: values.modelName || '',
        providerId: values.providerId || 0,
        width: w,
        height: h,
        numFrames,
        frameRate,
      })
      setGeneratedResult({
        name: result.name,
        filePath: result.filePath || (result as any).file_path,
        thumbnailPath: result.thumbnailPath || (result as any).thumbnail_path,
      })
      form.setFieldValue('name', result.name)
      message.success('生成成功')
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.message || '生成失败')
    }
  }, [form, onGenerate, message, sizeMode, customWidth, customHeight, numFrames, frameRate])

  const handleOk = useCallback(async () => {
    if (!generatedResult) {
      message.warning('请先生成视频')
      return
    }
    const values = await form.getFieldsValue()
    const [w, h] = sizeMode === 'custom'
      ? [customWidth, customHeight]
      : sizeMode.split('x').map(Number)
    const duration = numFrames / frameRate
    onOk({
      name: values.name || generatedResult.name,
      prompt: values.prompt,
      negativePrompt: values.negativePrompt || '',
      modelName: values.modelName || '',
      providerId: values.providerId || 0,
      filePath: generatedResult.filePath,
      thumbnailPath: generatedResult.thumbnailPath,
      tags: tags.join(','),
      width: w,
      height: h,
      numFrames,
      frameRate,
      duration: Math.round(duration * 100) / 100,
    })
    setGeneratedResult(null)
    setTags([])
    form.resetFields()
  }, [generatedResult, form, tags, onOk, message, sizeMode, customWidth, customHeight, numFrames, frameRate])

  const handleCancel = useCallback(() => {
    setGeneratedResult(null)
    setTags([])
    form.resetFields()
    onCancel()
  }, [form, onCancel])

  const addTag = useCallback(() => {
    const t = tagInput.trim()
    if (t && !tags.includes(t)) {
      setTags([...tags, t])
    }
    setTagInput('')
  }, [tagInput, tags])

  const handlePolish = useCallback(async () => {
    const content = form.getFieldValue('prompt')
    if (!content?.trim()) return
    setPolishing(true)
    try {
      const polished = await polishPrompt(content)
      form.setFieldValue('prompt', polished)
    } catch {
      // silent
    } finally {
      setPolishing(false)
    }
  }, [form])

  const handleGeneratePrompt = useCallback(async () => {
    const content = form.getFieldValue('prompt')
    if (!content?.trim()) return
    setGeneratingPrompt(true)
    try {
      const result = await generateVideoPrompt(content)
      form.setFieldValue('prompt', result)
    } catch {
      // silent
    } finally {
      setGeneratingPrompt(false)
    }
  }, [form])

  return (
    <Modal
      open={open}
      title="新增视频"
      width={1100}
      footer={null}
      onCancel={handleCancel}
    >
      <div className={styles.createLayout}>
        {/* 左侧：预览区 */}
        <div className={styles.previewWrap}>
          {isGenerating ? (
            <div style={{ textAlign: 'center', color: '#999' }}>
              <div className={styles.spinIcon}><HourglassOutlined /></div>
              <div>正在生成中...</div>
            </div>
          ) : generatedResult ? (
            <>
              <video src={toVideoUrl(generatedResult.filePath)} controls muted preload="metadata" style={{ maxWidth: '100%', maxHeight: '65vh' }} />
              <div style={{
                position: 'absolute', top: 8, left: 8,
                background: '#52c41a', color: '#fff', padding: '2px 8px',
                borderRadius: 4, fontSize: 12,
              }}>
                生成完成
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', color: '#999' }}>
              <div style={{ fontSize: 32, marginBottom: 8, color: 'var(--ant-color-text-tertiary)' }}><VideoCameraOutlined /></div>
              <div>输入提示词后点击「生成视频」</div>
            </div>
          )}
        </div>

        {/* 中间：提示词区 */}
        <div className={styles.createCenter}>
          <Form form={form} layout="vertical" size="small" style={{ flex: 1 }}>
            <Form.Item label="名称" name="name">
              <Input placeholder="留空自动生成" />
            </Form.Item>

            <Form.Item
              label={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                  <span>提示词</span>
                  <Space size={4}>
                    <Button
                      type="link" size="small"
                      icon={<ThunderboltOutlined />}
                      loading={generatingPrompt}
                      onClick={handleGeneratePrompt}
                      style={{ padding: 0, fontSize: 12 }}
                    >
                      生成内容
                    </Button>
                    <Button
                      type="link" size="small"
                      icon={<ThunderboltOutlined />}
                      loading={polishing}
                      onClick={handlePolish}
                      style={{ padding: 0, fontSize: 12 }}
                    >
                      润色内容
                    </Button>
                  </Space>
                </div>
              }
              name="prompt"
              rules={[{ required: true, message: '请输入提示词' }]}
            >
              <TextArea rows={6} placeholder="描述视频内容（英文效果更佳）&#10;推荐结构：[主体] + [动作] + [场景] + [镜头运动] + [光照] + [风格]&#10;例：A cat walking on the beach at sunset, cinematic tracking shot" style={{ resize: 'none' }} />
            </Form.Item>

            <Form.Item label="反向提示词" name="negativePrompt">
              <TextArea rows={3} placeholder="不希望出现的内容（可选）" style={{ resize: 'none' }} />
            </Form.Item>
          </Form>

          {/* 操作按钮 */}
          <div style={{ textAlign: 'center', paddingTop: 4 }}>
            {generatedResult ? (
              <Space>
                <Button onClick={() => setGeneratedResult(null)}>重新生成</Button>
                <Button type="primary" onClick={handleOk}>保存</Button>
              </Space>
            ) : (
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                loading={isGenerating}
                onClick={handleGenerate}
                size="large"
              >
                生成视频
              </Button>
            )}
          </div>
        </div>

        {/* 右侧：设置区 */}
        <div className={styles.createRight}>
          <Form form={form} layout="vertical" size="small">
            <Form.Item label="模型">
              <CompactModelSelect
                value={selectedModel}
                onChange={(_val, pid, modelName) => {
                  setSelectedModel(_val)
                  form.setFieldsValue({ modelName, providerId: pid })
                }}
                placeholder="选择模型"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item label="尺寸">
              <Select
                value={sizeMode}
                onChange={setSizeMode}
                options={SIZE_OPTIONS}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {sizeMode === 'custom' && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>宽度</div>
                  <InputNumber
                    value={customWidth}
                    onChange={(v) => setCustomWidth(v || 1152)}
                    min={256}
                    max={1920}
                    step={64}
                    style={{ width: '100%' }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>高度</div>
                  <InputNumber
                    value={customHeight}
                    onChange={(v) => setCustomHeight(v || 768)}
                    min={256}
                    max={1920}
                    step={64}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            )}

            <Form.Item label="帧数">
              <Select
                value={numFrames}
                onChange={setNumFrames}
                options={FRAME_OPTIONS}
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item label="帧率 (FPS)">
              <InputNumber
                value={frameRate}
                onChange={(v) => setFrameRate(v || 24)}
                min={1}
                max={60}
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item label="标签">
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onPressEnter={addTag}
                  placeholder="输入标签后回车"
                  style={{ flex: 1 }}
                />
                <Button icon={<PlusOutlined />} onClick={addTag}>添加</Button>
              </div>
              {existingTags.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: '#999' }}>已有标签：</span>
                  <Space wrap size={[0, 4]} style={{ marginTop: 4 }}>
                    {existingTags.filter((t) => !tags.includes(t)).map((t) => (
                      <Tag
                        key={t}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setTags([...tags, t])}
                      >
                        + {t}
                      </Tag>
                    ))}
                  </Space>
                </div>
              )}
              <Space wrap>
                {tags.map((t) => (
                  <Tag key={t} color="blue" closable onClose={() => setTags(tags.filter((x) => x !== t))}>
                    {t}
                  </Tag>
                ))}
              </Space>
            </Form.Item>
          </Form>
        </div>
      </div>
    </Modal>
  )
}
