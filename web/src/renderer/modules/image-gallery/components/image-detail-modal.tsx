/** 图片详情弹窗 */
import { useState, useCallback, useEffect } from 'react'
import {
  Modal, Form, Input, Button, Space, Tag, Popconfirm, App, Typography,
} from 'antd'
import { DeleteOutlined, ReloadOutlined, EditOutlined, CheckOutlined } from '@ant-design/icons'
import { useImageGallery } from '../hooks/use-image-gallery'
import type { ImageGallery, ImageGenerateInput } from '../types'
import styles from './image-gallery.module.css'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'

const { TextArea } = Input
const { Text } = Typography

function toImageUrl(filePath: string) {
  if (!filePath) return ''
  const filename = filePath.split(/[/\\]/).pop() || ''
  return `${API_BASE_URL}${API_PREFIX}/image_gallery/files/${encodeURIComponent(filename)}`
}

function fmtTime(s: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').replace(/\.\d+$/, '').slice(0, 19)
}

/** 旧图改名：原名-1, 原名-2 ... */
function incrName(baseName: string, existingNames: string[]): string {
  const base = baseName.replace(/-\d+$/, '')
  let n = 1
  while (existingNames.includes(`${base}-${n}`)) n++
  return `${base}-${n}`
}

interface ImageDetailModalProps {
  image: ImageGallery | null
  allImages: ImageGallery[]
  onClose: () => void
  onDelete: (id: number) => void
  onRegenerate: (input: ImageGenerateInput) => Promise<{ name: string; filePath: string; thumbnailPath: string; width: number; height: number }>
  isGenerating: boolean
}

export function ImageDetailModal({
  image,
  allImages,
  onClose,
  onDelete,
  onRegenerate,
  isGenerating,
}: ImageDetailModalProps) {
  const { message } = App.useApp()
  const { createImage, deleteImage, updateImage } = useImageGallery()
  const [editing, setEditing] = useState(false)
  const [form] = Form.useForm()
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [regenerated, setRegenerated] = useState<{
    filePath: string; name: string; prompt: string; negativePrompt: string
    modelName: string; providerId: number; width: number; height: number
  } | null>(null)

  useEffect(() => {
    if (image) {
      setEditing(false)
      setRegenerated(null)
      setTags(image.tags ? image.tags.split(',').filter(Boolean) : [])
      form.setFieldsValue({
        name: image.name,
        prompt: image.prompt,
        negativePrompt: image.negativePrompt,
      })
    }
  }, [image, form])

  const handleSave = useCallback(async () => {
    if (!image) return
    try {
      const values = await form.getFieldsValue()
      await updateImage(image.id, {
        name: values.name,
        prompt: values.prompt,
        negativePrompt: values.negativePrompt,
        tags: tags.join(','),
      })
      message.success('已更新')
      setEditing(false)
      onClose()
    } catch {
      message.error('更新失败')
    }
  }, [image, form, tags, updateImage, message, onClose])

  const handleRegenerate = useCallback(async () => {
    if (!image) return
    try {
      const result = await onRegenerate({
        prompt: image.prompt,
        negativePrompt: image.negativePrompt,
        modelName: image.modelName || 'agnes-image-2.1-flash',
        providerId: image.providerId || 0,
        width: image.width || 1024,
        height: image.height || 1024,
      })
      setRegenerated({
        filePath: result.filePath || (result as any).file_path,
        name: result.name,
        prompt: image.prompt,
        negativePrompt: image.negativePrompt,
        modelName: image.modelName,
        providerId: image.providerId,
        width: image.width || 1024,
        height: image.height || 1024,
      })
      message.success('生成成功，请确认')
    } catch (err: any) {
      message.error(err?.message || '重新生成失败')
    }
  }, [image, onRegenerate, message])

  const handleConfirm = useCallback(async () => {
    if (!image || !regenerated) return
    try {
      const oldNewName = incrName(image.name, allImages.map((i) => i.name))
      await updateImage(image.id, { name: oldNewName })
      await createImage({
        name: image.name,
        prompt: regenerated.prompt,
        negativePrompt: regenerated.negativePrompt,
        modelName: regenerated.modelName,
        providerId: regenerated.providerId,
        filePath: regenerated.filePath,
        thumbnailPath: regenerated.filePath,
        tags: image.tags || '',
        width: regenerated.width,
        height: regenerated.height,
      })
      await deleteImage(image.id)
      message.success(`原图已改名「${oldNewName}」并删除，新图已保存`)
      onClose()
    } catch {
      message.error('保存失败')
    }
  }, [image, regenerated, allImages, updateImage, createImage, deleteImage, message, onClose])

  const addTag = useCallback(() => {
    const t = tagInput.trim()
    if (t && !tags.includes(t)) {
      setTags([...tags, t])
    }
    setTagInput('')
  }, [tagInput, tags])

  if (!image) return null

  const previewSrc = regenerated
    ? toImageUrl(regenerated.filePath)
    : toImageUrl(image.filePath || (image as any).file_path)

  return (
    <Modal
      open={!!image}
      title={regenerated ? `${image.name} → 新生成` : image.name}
      width={900}
      footer={null}
      onCancel={onClose}
    >
      <div className={styles.detailLayout}>
        {/* 左侧大图 */}
        <div className={styles.detailImageWrap}>
          {isGenerating ? (
            <div style={{ textAlign: 'center', color: '#999' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>⏳</div>
              <div>正在生成中...</div>
            </div>
          ) : (
            <img src={previewSrc} alt={image.name} />
          )}
          {regenerated && (
            <div style={{
              position: 'absolute', top: 8, left: 8,
              background: '#52c41a', color: '#fff', padding: '2px 8px',
              borderRadius: 4, fontSize: 12,
            }}>
              新生成
            </div>
          )}
        </div>

        {/* 右侧信息 */}
        <div className={styles.detailSidebar}>
          {editing ? (
            <Form form={form} layout="vertical" size="small">
              <Form.Item label="名称" name="name"><Input /></Form.Item>
              <Form.Item label="提示词" name="prompt"><TextArea rows={3} /></Form.Item>
              <Form.Item label="反向提示词" name="negativePrompt"><TextArea rows={2} /></Form.Item>
              <Form.Item label="标签">
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <Input value={tagInput} onChange={(e) => setTagInput(e.target.value)} onPressEnter={addTag} placeholder="回车添加" size="small" />
                  <Button size="small" onClick={addTag}>添加</Button>
                </div>
                <Space wrap>
                  {tags.map((t) => (
                    <Tag key={t} closable onClose={() => setTags(tags.filter((x) => x !== t))}>{t}</Tag>
                  ))}
                </Space>
              </Form.Item>
            </Form>
          ) : (
            <>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>提示词</Text>
                <div style={{ marginTop: 4, fontSize: 13 }}>{regenerated?.prompt || image.prompt}</div>
              </div>
              {(regenerated?.negativePrompt || image.negativePrompt) && (
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>反向提示词</Text>
                  <div style={{ marginTop: 4, fontSize: 13 }}>{regenerated?.negativePrompt || image.negativePrompt}</div>
                </div>
              )}
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>标签</Text>
                <div style={{ marginTop: 4 }}>
                  <Space wrap>
                    {tags.length > 0 ? tags.map((t) => <Tag key={t}>{t}</Tag>) : <Text type="secondary">无</Text>}
                  </Space>
                </div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>模型</Text>
                <div style={{ marginTop: 4, fontSize: 13 }}>{image.modelName || '未知'}</div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>尺寸</Text>
                <div style={{ marginTop: 4, fontSize: 13 }}>{image.width} x {image.height}</div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>创建时间</Text>
                <div style={{ marginTop: 4, fontSize: 13 }}>{fmtTime(image.createdAt)}</div>
              </div>
            </>
          )}

          {/* 操作按钮 */}
          <Space style={{ marginTop: 'auto' }} wrap>
            {editing ? (
              <>
                <Button type="primary" size="small" onClick={handleSave}>保存</Button>
                <Button size="small" onClick={() => setEditing(false)}>取消</Button>
              </>
            ) : regenerated ? (
              <>
                <Button type="primary" size="small" icon={<CheckOutlined />} onClick={handleConfirm}>
                  确认生成（原图删除）
                </Button>
                <Button size="small" onClick={() => setRegenerated(null)}>放弃</Button>
              </>
            ) : (
              <>
                <Button size="small" icon={<EditOutlined />} onClick={() => setEditing(true)}>编辑</Button>
                <Button size="small" icon={<ReloadOutlined />} loading={isGenerating} onClick={handleRegenerate}>重新生成</Button>
                <Popconfirm title="确定删除此图片？" onConfirm={() => onDelete(image.id)}>
                  <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>
              </>
            )}
          </Space>
        </div>
      </div>
    </Modal>
  )
}
