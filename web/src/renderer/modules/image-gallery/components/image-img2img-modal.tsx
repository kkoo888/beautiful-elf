/** 图生图弹窗 — 用编辑样式（左图右表单） */
import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Modal, Form, Input, Button, Space, App, Upload, Typography,
} from 'antd'
import { UploadOutlined, ThunderboltOutlined, LoadingOutlined, PictureOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd'
import { CompactModelSelect, getProvidersCached } from '@/modules/shared/components/model-selector'
import { polishPrompt } from '@/modules/expert-team/services/expert-team-api'
import { generateImagePrompt, describeImage } from '../services/image-gallery-api'
import type { ImageImg2ImgInput, ImageGenerateResult } from '../types'
import styles from './image-gallery.module.css'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'

const { TextArea } = Input
const { Text } = Typography

function toImageUrl(filePath: string) {
  if (!filePath) return ''
  const filename = filePath.split(/[/\\]/).pop() || ''
  return `${API_BASE_URL}${API_PREFIX}/image_gallery/files/${encodeURIComponent(filename)}`
}

interface ImageImg2ImgModalProps {
  open: boolean
  onOk: (input: ImageImg2ImgInput) => Promise<ImageGenerateResult>
  isGenerating: boolean
  onCancel: () => void
}

export function ImageImg2ImgModal({
  open,
  onOk,
  isGenerating,
  onCancel,
}: ImageImg2ImgModalProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [selectedModel, setSelectedModel] = useState('')
  const [polishing, setPolishing] = useState(false)
  const [generatingPrompt, setGeneratingPrompt] = useState(false)
  const [describing, setDescribing] = useState(false)

  const [initImagePreview, setInitImagePreview] = useState('')
  const [initImageBase64, setInitImageBase64] = useState('')

  const [result, setResult] = useState<ImageGenerateResult | null>(null)

  useEffect(() => {
    if (open) {
      setResult(null)
      setInitImagePreview('')
      setInitImageBase64('')
      form.resetFields()
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

  const handleUploadImage = useCallback(async (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const dataUri = e.target?.result as string
      setInitImagePreview(dataUri)
      setInitImageBase64(dataUri)
    }
    reader.readAsDataURL(file)
    return false
  }, [])

  const handleGenerate = useCallback(async () => {
    if (!initImageBase64) {
      message.warning('请先上传原图')
      return
    }
    try {
      const values = await form.validateFields(['prompt', 'negativePrompt', 'modelName', 'providerId'])
      const genResult = await onOk({
        prompt: values.prompt,
        negativePrompt: values.negativePrompt || '',
        modelName: values.modelName || '',
        providerId: values.providerId || 0,
        image: initImageBase64,
      })
      setResult({
        filePath: genResult.filePath || (genResult as any).file_path,
        thumbnailPath: genResult.thumbnailPath || (genResult as any).thumbnail_path,
        name: genResult.name,
      })
      message.success('生成成功')
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.message || '生成失败')
    }
  }, [form, onOk, initImageBase64, message])

  const handlePolish = useCallback(async () => {
    const content = form.getFieldValue('prompt')
    if (!content?.trim()) return
    setPolishing(true)
    try {
      const polished = await polishPrompt(content)
      form.setFieldValue('prompt', polished)
    } catch { /* silent */ } finally {
      setPolishing(false)
    }
  }, [form])

  const handleGeneratePrompt = useCallback(async () => {
    const content = form.getFieldValue('prompt')
    if (!content?.trim()) return
    setGeneratingPrompt(true)
    try {
      const r = await generateImagePrompt(content)
      form.setFieldValue('prompt', r)
    } catch { /* silent */ } finally {
      setGeneratingPrompt(false)
    }
  }, [form])

  const handleDescribeImage = useCallback(async () => {
    if (!initImageBase64) {
      message.warning('请先上传原图')
      return
    }
    setDescribing(true)
    try {
      const r = await describeImage(initImageBase64)
      form.setFieldValue('prompt', r)
      message.success('图片解析完成')
    } catch { /* silent */ } finally {
      setDescribing(false)
    }
  }, [initImageBase64, form, message])

  const handleClose = useCallback(() => {
    setResult(null)
    setInitImagePreview('')
    setInitImageBase64('')
    form.resetFields()
    onCancel()
  }, [form, onCancel])

  return (
    <Modal
      open={open}
      title="图生图"
      width={1100}
      footer={null}
      onCancel={handleClose}
    >
      <div className={styles.createLayout}>
        {/* 左侧：原图 / 结果预览 */}
        <div className={styles.detailImageWrap} style={{ flex: '0 0 380px' }}>
          {isGenerating ? (
            <div style={{ textAlign: 'center', color: '#999' }}>
              <div style={{ fontSize: 32, marginBottom: 8, color: 'var(--ant-color-primary)' }}><LoadingOutlined spin /></div>
              <div>正在生成中...</div>
            </div>
          ) : result ? (
            <>
              <img src={toImageUrl(result.filePath)} alt={result.name} />
              <div style={{
                position: 'absolute', top: 8, left: 8,
                background: '#52c41a', color: '#fff', padding: '2px 8px',
                borderRadius: 4, fontSize: 12,
              }}>
                生成完成
              </div>
            </>
          ) : initImagePreview ? (
            <img src={initImagePreview} alt="原图预览" />
          ) : (
            <div style={{ textAlign: 'center', color: '#999' }}>
              <div style={{ fontSize: 32, marginBottom: 8, color: 'var(--ant-color-text-tertiary)' }}><PictureOutlined /></div>
              <div>上传原图后在此预览</div>
            </div>
          )}
        </div>

        {/* 中间：提示词区 */}
        <div className={styles.createCenter}>
          <Form form={form} layout="vertical" size="small" style={{ flex: 1 }}>
            <Form.Item label="上传原图" required>
              <Upload
                accept="image/*"
                showUploadList={false}
                beforeUpload={handleUploadImage}
              >
                <Button icon={<UploadOutlined />} block>
                  {initImagePreview ? '重新上传' : '选择图片'}
                </Button>
              </Upload>
            </Form.Item>

            <Form.Item
              label={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                  <span>提示词</span>
                  <Space size={4}>
                    <Button
                      type="link" size="small"
                      icon={<ThunderboltOutlined />}
                      loading={describing}
                      onClick={handleDescribeImage}
                      style={{ padding: 0, fontSize: 12 }}
                      disabled={!initImageBase64}
                    >
                      解析图片
                    </Button>
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
              <TextArea rows={6} placeholder="描述你想要的新图片内容..." style={{ resize: 'none' }} />
            </Form.Item>

            <Form.Item label="反向提示词" name="negativePrompt">
              <TextArea rows={3} placeholder="不希望出现的内容（可选）" style={{ resize: 'none' }} />
            </Form.Item>
          </Form>

          {/* 操作按钮 */}
          <div style={{ textAlign: 'center', paddingTop: 4 }}>
            {result ? (
              <Space>
                <Button onClick={() => setResult(null)}>重新生成</Button>
                <Button onClick={handleClose}>关闭</Button>
              </Space>
            ) : (
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                loading={isGenerating}
                onClick={handleGenerate}
                size="large"
                disabled={!initImageBase64}
              >
                生成图片
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
          </Form>
        </div>
      </div>
    </Modal>
  )
}
