/** 新增图片弹窗 */
import { useState, useCallback, useEffect } from 'react'
import {
  Modal, Form, Input, Select, Button, Space, Tag, App, InputNumber,
} from 'antd'
import { ThunderboltOutlined, PlusOutlined } from '@ant-design/icons'
import { CompactModelSelect, getProvidersCached } from '@/modules/shared/components/model-selector'
import { polishPrompt } from '@/modules/expert-team/services/expert-team-api'
import { fetchImageTags, generateImagePrompt } from '../services/image-gallery-api'
import type { ImageGalleryFormInput, ImageGenerateInput } from '../types'
import styles from './image-gallery.module.css'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'

const { TextArea } = Input

/** 将本地路径转为 API URL */
function toImageUrl(filePath: string) {
  if (!filePath) return ''
  const filename = filePath.split(/[/\\]/).pop() || ''
  return `${API_BASE_URL}${API_PREFIX}/image_gallery/files/${encodeURIComponent(filename)}`
}

/** 预设尺寸选项 */
const SIZE_OPTIONS = [
  { label: '1024 x 1024', value: '1024x1024' },
  { label: '1024 x 768 (4:3)', value: '1024x768' },
  { label: '768 x 1024 (3:4)', value: '768x1024' },
  { label: '1024 x 576 (16:9)', value: '1024x576' },
  { label: '576 x 1024 (9:16)', value: '576x1024' },
  { label: '自定义', value: 'custom' },
]

interface ImageCreateModalProps {
  open: boolean
  onOk: (input: ImageGalleryFormInput) => void
  onGenerate: (input: ImageGenerateInput) => Promise<{ name: string; filePath: string; thumbnailPath: string; width: number; height: number }>
  isGenerating: boolean
  onCancel: () => void
}

export function ImageCreateModal({
  open,
  onOk,
  onGenerate,
  isGenerating,
  onCancel,
}: ImageCreateModalProps) {
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
  const [sizeMode, setSizeMode] = useState('1024x1024')
  const [customWidth, setCustomWidth] = useState(1024)
  const [customHeight, setCustomHeight] = useState(1024)
  const [selectedModel, setSelectedModel] = useState('')

  // 打开弹窗时设置默认模型 + 加载已有标签
  useEffect(() => {
    if (open) {
      setTags([])
      setSelectedModel('')
      // 加载已有标签
      fetchImageTags().then((t) => setExistingTags(t)).catch(() => {})
      // 查找默认模型
      getProvidersCached().then((providers) => {
        for (const p of providers) {
          const m = p.models?.find((m) => m.modelName === 'agnes-image-2.1-flash')
          if (m) {
            setSelectedModel(`${p.id}:agnes-image-2.1-flash`)
            form.setFieldsValue({ modelName: 'agnes-image-2.1-flash', providerId: p.id })
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
  }, [form, onGenerate, message])

  const handleOk = useCallback(async () => {
    if (!generatedResult) {
      message.warning('请先生成图片')
      return
    }
    const values = await form.getFieldsValue()
    const [w, h] = sizeMode === 'custom'
      ? [customWidth, customHeight]
      : sizeMode.split('x').map(Number)
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
    })
    setGeneratedResult(null)
    setTags([])
    form.resetFields()
  }, [generatedResult, form, tags, onOk, message])

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
      const result = await generateImagePrompt(content)
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
      title="新增图片"
      width={640}
      okText="保存"
      cancelText="取消"
      onOk={handleOk}
      onCancel={handleCancel}
      okButtonProps={{ disabled: !generatedResult }}
    >
      <Form form={form} layout="vertical">
        <Form.Item label="名称" name="name">
          <Input placeholder="留空自动生成古风名" />
        </Form.Item>

        <Form.Item
          label={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <span>提示词</span>
              <Space size={4}>
                <Button
                  type="link"
                  size="small"
                  icon={<ThunderboltOutlined />}
                  loading={generatingPrompt}
                  onClick={handleGeneratePrompt}
                  style={{ padding: 0, fontSize: 12 }}
                >
                  生成内容
                </Button>
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
              </Space>
            </div>
          }
          name="prompt"
          rules={[{ required: true, message: '请输入提示词' }]}
        >
          <TextArea rows={3} placeholder="描述你想生成的图片内容..." />
        </Form.Item>

        <Form.Item label="反向提示词" name="negativePrompt">
          <TextArea rows={2} placeholder="不希望出现的内容（可选）" />
        </Form.Item>

        <div style={{ display: 'flex', gap: 12 }}>
          <Form.Item label="模型" style={{ flex: 1 }}>
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
          <Form.Item label="尺寸" style={{ flex: 1 }}>
            <Select
              value={sizeMode}
              onChange={setSizeMode}
              options={SIZE_OPTIONS}
              style={{ width: '100%' }}
            />
          </Form.Item>
        </div>

        {sizeMode === 'custom' && (
          <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>宽度</div>
              <InputNumber
                value={customWidth}
                onChange={(v) => setCustomWidth(v || 1024)}
                min={256}
                max={4096}
                step={64}
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>高度</div>
              <InputNumber
                value={customHeight}
                onChange={(v) => setCustomHeight(v || 1024)}
                min={256}
                max={4096}
                step={64}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        )}

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
          {/* 已有标签可点击选择 */}
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
          {/* 已选标签 */}
          <Space wrap>
            {tags.map((t) => (
              <Tag key={t} color="blue" closable onClose={() => setTags(tags.filter((x) => x !== t))}>
                {t}
              </Tag>
            ))}
          </Space>
        </Form.Item>

        {/* 生成按钮 + 预览 */}
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={isGenerating}
            onClick={handleGenerate}
            size="large"
          >
            生成图片
          </Button>
        </div>

        <div className={styles.generatePreview}>
          {generatedResult ? (
            <img src={toImageUrl(generatedResult.filePath)} alt="预览" />
          ) : (
            <span style={{ color: '#999' }}>输入提示词后点击「生成图片」</span>
          )}
        </div>
      </Form>
    </Modal>
  )
}
