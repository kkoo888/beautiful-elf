/** 新增图片弹窗 */
import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Modal, Form, Input, Select, Button, Space, Tag, App, InputNumber,
} from 'antd'
import {
  ThunderboltOutlined, PlusOutlined, LoadingOutlined, PictureOutlined,
  LeftOutlined, RightOutlined,
} from '@ant-design/icons'
import { CompactModelSelect, getProvidersCached } from '@/modules/shared/components/model-selector'
import { polishPrompt } from '@/modules/expert-team/services/expert-team-api'
import { fetchImageTags, generateImagePrompt } from '../services/image-gallery-api'
import type { ImageGalleryFormInput, ImageGenerateInput, ImageGenerateResult } from '../types'
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
  { label: '──────────── 2K ────────────', value: '__sep_2k', disabled: true },
  { label: '2K 横 2048 x 1152 (16:9)', value: '2048x1152' },
  { label: '2K 竖 1152 x 2048 (9:16)', value: '1152x2048' },
  { label: '2K 横 2048 x 1536 (4:3)', value: '2048x1536' },
  { label: '2K 竖 1536 x 2048 (3:4)', value: '1536x2048' },
  { label: '──────────── 4K ────────────', value: '__sep_4k', disabled: true },
  { label: '4K 横 3840 x 2160 (16:9)', value: '3840x2160' },
  { label: '4K 竖 2160 x 3840 (9:16)', value: '2160x3840' },
  { label: '4K 横 3840 x 2880 (4:3)', value: '3840x2880' },
  { label: '4K 竖 2880 x 3840 (3:4)', value: '2880x3840' },
  { label: '──────────── 6K ────────────', value: '__sep_6k', disabled: true },
  { label: '6K 横 6144 x 3456 (16:9)', value: '6144x3456' },
  { label: '6K 竖 3456 x 6144 (9:16)', value: '3456x6144' },
  { label: '6K 横 6144 x 4608 (4:3)', value: '6144x4608' },
  { label: '6K 竖 4608 x 6144 (3:4)', value: '4608x6144' },
  { label: '──────────── 8K ────────────', value: '__sep_8k', disabled: true },
  { label: '8K 横 7680 x 4320 (16:9)', value: '7680x4320' },
  { label: '8K 竖 4320 x 7680 (9:16)', value: '4320x7680' },
  { label: '8K 横 7680 x 5760 (4:3)', value: '7680x5760' },
  { label: '8K 竖 5760 x 7680 (3:4)', value: '5760x7680' },
  { label: '──────────── 自定义 ────────────', value: '__sep_custom', disabled: true },
  { label: '自定义', value: 'custom' },
]

/** 兼容 snake_case / camelCase 返回 */
function normalizeResult(r: any): ImageGenerateResult {
  return {
    name: r.name,
    filePath: r.filePath || r.file_path || '',
    thumbnailPath: r.thumbnailPath || r.thumbnail_path || '',
    width: r.width,
    height: r.height,
  }
}

interface ImageCreateModalProps {
  open: boolean
  onOk: (input: ImageGalleryFormInput) => void
  onGenerate: (input: ImageGenerateInput) => Promise<ImageGenerateResult>
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
  const [generatedResults, setGeneratedResults] = useState<ImageGenerateResult[]>([])
  const [currentSlide, setCurrentSlide] = useState(0)
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number } | null>(null)
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [existingTags, setExistingTags] = useState<string[]>([])
  const [polishing, setPolishing] = useState(false)
  const [generatingPrompt, setGeneratingPrompt] = useState(false)
  const [sizeMode, setSizeMode] = useState('1024x1024')
  const [customWidth, setCustomWidth] = useState(1024)
  const [customHeight, setCustomHeight] = useState(1024)
  const [selectedModel, setSelectedModel] = useState('')
  const [imageCount, setImageCount] = useState(1)
  const [selectedSlides, setSelectedSlides] = useState<Set<number>>(new Set([0]))
  const abortRef = useRef(false)

  // 打开弹窗时设置默认模型 + 加载已有标签
  useEffect(() => {
    if (open) {
      setTags([])
      setSelectedModel('')
      setGeneratedResults([])
      setCurrentSlide(0)
      setSelectedSlides(new Set([0]))
      setBatchProgress(null)
      abortRef.current = false
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
      const generateInput: ImageGenerateInput = {
        prompt: values.prompt,
        negativePrompt: values.negativePrompt || '',
        modelName: values.modelName || '',
        providerId: values.providerId || 0,
        width: w,
        height: h,
      }

      if (imageCount <= 1) {
        // 单张直接生成
        const raw = await onGenerate(generateInput)
        const result = normalizeResult(raw)
        setGeneratedResults([result])
        setCurrentSlide(0)
        form.setFieldValue('name', result.name)
        message.success('生成成功')
      } else {
        // 批量生成：每 50ms 发一个请求，回来一个放一个
        abortRef.current = false
        setBatchProgress({ current: 0, total: imageCount })
        let completed = 0
        const results: ImageGenerateResult[] = []
        let firstResult = true

        const fireOne = (index: number) => {
          onGenerate(generateInput).then((raw) => {
            if (abortRef.current) return
            const result = normalizeResult(raw)
            results.push(result)
            completed++
            setBatchProgress({ current: completed, total: imageCount })
            setGeneratedResults([...results])
            if (firstResult) {
              firstResult = false
              setCurrentSlide(0)
              form.setFieldValue('name', result.name)
            }
            if (completed === imageCount) {
              setBatchProgress(null)
              message.success(`生成完成，共 ${results.length} 张`)
            }
          }).catch(() => {
            if (abortRef.current) return
            completed++
            setBatchProgress({ current: completed, total: imageCount })
            if (completed === imageCount) {
              setBatchProgress(null)
              if (results.length > 0) {
                message.success(`生成完成，共 ${results.length} 张`)
              } else {
                message.error('生成失败')
              }
            }
          })
        }

        for (let i = 0; i < imageCount; i++) {
          if (abortRef.current) break
          fireOne(i)
          // 50ms 间隔发下一个请求
          if (i < imageCount - 1 && !abortRef.current) {
            await new Promise((r) => setTimeout(r, 50))
          }
        }
      }
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.message || '生成失败')
    }
  }, [form, onGenerate, message, sizeMode, customWidth, customHeight, imageCount])

  const handleOk = useCallback(async () => {
    if (generatedResults.length === 0) {
      message.warning('请先生成图片')
      return
    }
    const values = await form.getFieldsValue()
    const [w, h] = sizeMode === 'custom'
      ? [customWidth, customHeight]
      : sizeMode.split('x').map(Number)
    // 只保存选中的图片
    const toSave = generatedResults.filter((_, i) => selectedSlides.has(i))
    if (toSave.length === 0) {
      message.warning('请至少选择一张图片')
      return
    }
    for (const result of toSave) {
      await onOk({
        name: values.name || result.name,
        prompt: values.prompt,
        negativePrompt: values.negativePrompt || '',
        modelName: values.modelName || '',
        providerId: values.providerId || 0,
        filePath: result.filePath,
        thumbnailPath: result.thumbnailPath,
        tags: tags.join(','),
        width: w,
        height: h,
      })
    }
    setGeneratedResults([])
    setCurrentSlide(0)
    setSelectedSlides(new Set([0]))
    setTags([])
    form.resetFields()
  }, [generatedResults, form, tags, onOk, message, sizeMode, customWidth, customHeight])

  const handleCancel = useCallback(() => {
    abortRef.current = true
    setGeneratedResults([])
    setCurrentSlide(0)
    setSelectedSlides(new Set([0]))
    setBatchProgress(null)
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

  const isBatching = batchProgress !== null
  const hasResults = generatedResults.length > 0
  const currentResult = hasResults ? generatedResults[currentSlide] : null

  return (
    <Modal
      open={open}
      title="新增图片"
      width={1100}
      footer={null}
      onCancel={handleCancel}
    >
      <div className={styles.createLayout}>
        {/* 左侧：预览区（轮播图）+ 圆圈选择器 */}
        <div style={{ flex: '0 0 380px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div className={styles.detailImageWrap}>
            {hasResults ? (
              <div className={styles.carouselWrap}>
                <img
                  className={styles.carouselImage}
                  src={toImageUrl(currentResult!.filePath)}
                  alt={`预览 ${currentSlide + 1}`}
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none'
                  }}
                />
                {/* 生成完成标签 */}
                <div style={{
                  position: 'absolute', top: 8, left: 8,
                  background: '#52c41a', color: '#fff', padding: '2px 8px',
                  borderRadius: 4, fontSize: 12,
                }}>
                  {selectedSlides.has(currentSlide) ? '已选中' : '未选中'}
                </div>
                {/* 多张时显示轮播控制 */}
                {generatedResults.length > 1 && (
                  <>
                    <button
                      className={`${styles.carouselArrow} ${styles.carouselArrowLeft}`}
                      onClick={() => setCurrentSlide((s) => (s > 0 ? s - 1 : generatedResults.length - 1))}
                    >
                      <LeftOutlined />
                    </button>
                    <button
                      className={`${styles.carouselArrow} ${styles.carouselArrowRight}`}
                      onClick={() => setCurrentSlide((s) => (s < generatedResults.length - 1 ? s + 1 : 0))}
                    >
                      <RightOutlined />
                    </button>
                    <div className={styles.carouselCounter}>
                      {currentSlide + 1} / {generatedResults.length}
                    </div>
                  </>
                )}
                {/* 批量生成进度 */}
                {isBatching && batchProgress && (
                  <div className={styles.carouselProgress}>
                    {batchProgress.current}/{batchProgress.total}
                  </div>
                )}
              </div>
            ) : isBatching || isGenerating ? (
              <div style={{ textAlign: 'center', color: '#999' }}>
                <div style={{ fontSize: 32, marginBottom: 8, color: 'var(--ant-color-primary)' }}><LoadingOutlined spin /></div>
                <div>正在生成中...</div>
                {isBatching && batchProgress && (
                  <div style={{ marginTop: 8, fontSize: 13, color: 'var(--ant-color-primary)' }}>
                    {batchProgress.current} / {batchProgress.total}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', color: '#999' }}>
                <div style={{ fontSize: 32, marginBottom: 8, color: 'var(--ant-color-text-tertiary)' }}><PictureOutlined /></div>
                <div>输入提示词后点击「生成图片」</div>
              </div>
            )}
          </div>
          {/* 圆圈选择器 — 在图片容器外面，不受 overflow:hidden 影响 */}
          {hasResults && generatedResults.length > 1 && (
            <div className={styles.carouselDots}>
              {generatedResults.map((_, i) => (
                <button
                  key={i}
                  className={`${styles.carouselDot} ${selectedSlides.has(i) ? styles.carouselDotSelected : ''}`}
                  onClick={() => {
                    setCurrentSlide(i)
                    setSelectedSlides((prev) => {
                      const next = new Set(prev)
                      if (next.has(i)) next.delete(i)
                      else next.add(i)
                      return next
                    })
                  }}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 中间：提示词区 */}
        <div className={styles.createCenter}>
          <Form form={form} layout="vertical" size="small" style={{ flex: 1 }}>
            <Form.Item label="名称" name="name">
              <Input placeholder="留空自动生成古风名" />
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
              <TextArea rows={6} placeholder="描述你想生成的图片内容..." style={{ resize: 'none' }} />
            </Form.Item>

            <Form.Item label="反向提示词" name="negativePrompt">
              <TextArea rows={3} placeholder="不希望出现的内容（可选）" style={{ resize: 'none' }} />
            </Form.Item>
          </Form>

          {/* 操作按钮 */}
          <div style={{ textAlign: 'center', paddingTop: 4 }}>
            {hasResults && !isBatching ? (
              <Space>
                <Button onClick={() => { setGeneratedResults([]); setCurrentSlide(0); setSelectedSlides(new Set([0])) }}>重新生成</Button>
                <Button
                  type="primary"
                  onClick={handleOk}
                  disabled={selectedSlides.size === 0}
                >保存{generatedResults.length > 1 ? ` (${selectedSlides.size}/${generatedResults.length})` : ''}</Button>
              </Space>
            ) : (
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                loading={isGenerating}
                onClick={handleGenerate}
                size="large"
                disabled={isBatching}
              >
                {isBatching ? `生成中 ${batchProgress?.current}/${batchProgress?.total}` : '生成图片'}
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
                    onChange={(v) => setCustomWidth(v || 1024)}
                    min={256}
                    max={7680}
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
                    max={7680}
                    step={64}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            )}

            <Form.Item label="生成张数">
              <Space.Compact style={{ width: '100%' }}>
                <InputNumber
                  value={imageCount}
                  onChange={(v) => setImageCount(v || 1)}
                  min={1}
                  max={20}
                  style={{ flex: 1 }}
                />
                <span style={{
                  display: 'flex', alignItems: 'center', padding: '0 12px',
                  background: 'var(--ant-color-fill-secondary)',
                  border: '1px solid var(--ant-color-border)',
                  borderLeft: 'none',
                  borderRadius: '0 6px 6px 0',
                  fontSize: 13, color: 'var(--ant-color-text-secondary)',
                  whiteSpace: 'nowrap',
                }}>张</span>
              </Space.Compact>
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
