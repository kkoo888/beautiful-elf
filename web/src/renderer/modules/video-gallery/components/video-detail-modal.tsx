/** 视频详情弹窗 — 三栏布局 */
import { useState, useCallback, useEffect } from 'react'
import {
  Modal, Form, Input, Button, Space, Tag, Popconfirm, App, Typography,
} from 'antd'
import { DeleteOutlined, ReloadOutlined, EditOutlined, CheckOutlined, HourglassOutlined } from '@ant-design/icons'
import { useVideoGallery } from '../hooks/use-video-gallery'
import type { VideoGallery, VideoGenerateInput } from '../types'
import styles from './video-gallery.module.css'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'

const { TextArea } = Input
const { Text } = Typography

function toVideoUrl(filePath: string) {
  if (!filePath) return ''
  const filename = filePath.split(/[/\\]/).pop() || ''
  return `${API_BASE_URL}${API_PREFIX}/video_gallery/files/${encodeURIComponent(filename)}`
}

function fmtTime(s: string | null) {
  if (!s) return '-'
  return s.replace('T', ' ').replace(/\.\d+$/, '').slice(0, 19)
}

function formatDuration(seconds: number) {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`
}

function incrName(baseName: string, existingNames: string[]): string {
  const base = baseName.replace(/-\d+$/, '')
  let n = 1
  while (existingNames.includes(`${base}-${n}`)) n++
  return `${base}-${n}`
}

interface VideoDetailModalProps {
  video: VideoGallery | null
  allVideos: VideoGallery[]
  onClose: () => void
  onDelete: (id: number) => void
  onRegenerate: (input: VideoGenerateInput) => Promise<{ name: string; filePath: string; thumbnailPath: string; width: number; height: number; numFrames: number; frameRate: number; duration: number }>
  isGenerating: boolean
}

export function VideoDetailModal({
  video,
  allVideos,
  onClose,
  onDelete,
  onRegenerate,
  isGenerating,
}: VideoDetailModalProps) {
  const { message } = App.useApp()
  const { createVideo, deleteVideo, updateVideo } = useVideoGallery()
  const [editing, setEditing] = useState(false)
  const [form] = Form.useForm()
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [regenerated, setRegenerated] = useState<{
    filePath: string; name: string; prompt: string; negativePrompt: string
    modelName: string; providerId: number; width: number; height: number
    numFrames: number; frameRate: number; duration: number
  } | null>(null)

  useEffect(() => {
    if (video) {
      setEditing(false)
      setRegenerated(null)
      setTags(video.tags ? video.tags.split(',').filter(Boolean) : [])
      form.setFieldsValue({
        name: video.name,
        prompt: video.prompt,
        negativePrompt: video.negativePrompt,
      })
    }
  }, [video, form])

  const handleSave = useCallback(async () => {
    if (!video) return
    try {
      const values = await form.getFieldsValue()
      await updateVideo(video.id, {
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
  }, [video, form, tags, updateVideo, message, onClose])

  const handleRegenerate = useCallback(async () => {
    if (!video) return
    try {
      const result = await onRegenerate({
        prompt: video.prompt,
        negativePrompt: video.negativePrompt,
        modelName: video.modelName || 'agnes-video-v2.0',
        providerId: video.providerId || 0,
        width: video.width || 1280,
        height: video.height || 720,
        numFrames: video.numFrames || 121,
        frameRate: video.frameRate || 24,
      })
      setRegenerated({
        filePath: result.filePath || (result as any).file_path,
        name: result.name,
        prompt: video.prompt,
        negativePrompt: video.negativePrompt,
        modelName: video.modelName,
        providerId: video.providerId,
        width: video.width || 1280,
        height: video.height || 720,
        numFrames: video.numFrames || 121,
        frameRate: video.frameRate || 24,
        duration: video.duration || 0,
      })
      message.success('生成成功，请确认')
    } catch (err: any) {
      message.error(err?.message || '重新生成失败')
    }
  }, [video, onRegenerate, message])

  const handleConfirm = useCallback(async () => {
    if (!video || !regenerated) return
    try {
      const oldNewName = incrName(video.name, allVideos.map((v) => v.name))
      await updateVideo(video.id, { name: oldNewName })
      await createVideo({
        name: video.name,
        prompt: regenerated.prompt,
        negativePrompt: regenerated.negativePrompt,
        modelName: regenerated.modelName,
        providerId: regenerated.providerId,
        filePath: regenerated.filePath,
        thumbnailPath: regenerated.filePath,
        tags: video.tags || '',
        width: regenerated.width,
        height: regenerated.height,
        numFrames: regenerated.numFrames,
        frameRate: regenerated.frameRate,
        duration: regenerated.duration,
      })
      await deleteVideo(video.id)
      message.success(`原视频已改名「${oldNewName}」并删除，新视频已保存`)
      onClose()
    } catch {
      message.error('保存失败')
    }
  }, [video, regenerated, allVideos, updateVideo, createVideo, deleteVideo, message, onClose])

  const addTag = useCallback(() => {
    const t = tagInput.trim()
    if (t && !tags.includes(t)) {
      setTags([...tags, t])
    }
    setTagInput('')
  }, [tagInput, tags])

  if (!video) return null

  const previewSrc = regenerated
    ? toVideoUrl(regenerated.filePath)
    : toVideoUrl(video.filePath || (video as any).file_path)

  return (
    <Modal
      open={!!video}
      title={regenerated ? `${video.name} → 新生成` : video.name}
      width={1100}
      footer={null}
      onCancel={onClose}
    >
      <div className={styles.createLayout}>
        {/* 左侧：视频预览 */}
        <div className={styles.previewWrap}>
          {isGenerating ? (
            <div style={{ textAlign: 'center', color: '#999' }}>
              <div className={styles.spinIcon}><HourglassOutlined /></div>
              <div>正在生成中...</div>
            </div>
          ) : (
            <video src={previewSrc} controls muted preload="metadata" style={{ maxWidth: '100%', maxHeight: '65vh' }} />
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

        {/* 中间：提示词区 */}
        <div className={styles.createCenter}>
          {editing ? (
            <Form form={form} layout="vertical" size="small" style={{ flex: 1 }}>
              <Form.Item label="名称" name="name"><Input /></Form.Item>
              <Form.Item label="提示词" name="prompt"><TextArea rows={6} style={{ resize: 'none' }} /></Form.Item>
              <Form.Item label="反向提示词" name="negativePrompt"><TextArea rows={3} style={{ resize: 'none' }} /></Form.Item>
            </Form>
          ) : (
            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>提示词</Text>
                <div style={{ marginTop: 4, fontSize: 13, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                  {regenerated?.prompt || video.prompt}
                </div>
              </div>
              {(regenerated?.negativePrompt || video.negativePrompt) && (
                <div style={{ marginBottom: 16 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>反向提示词</Text>
                  <div style={{ marginTop: 4, fontSize: 13, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                    {regenerated?.negativePrompt || video.negativePrompt}
                  </div>
                </div>
              )}
            </div>
          )}
          {/* 操作按钮 */}
          <div style={{ textAlign: 'center', paddingTop: 4 }}>
            {editing ? (
              <Space>
                <Button type="primary" size="small" onClick={handleSave}>保存</Button>
                <Button size="small" onClick={() => setEditing(false)}>取消</Button>
              </Space>
            ) : regenerated ? (
              <Space>
                <Button type="primary" size="small" icon={<CheckOutlined />} onClick={handleConfirm}>
                  确认生成（原视频删除）
                </Button>
                <Button size="small" onClick={() => setRegenerated(null)}>放弃</Button>
              </Space>
            ) : (
              <Space>
                <Button size="small" icon={<EditOutlined />} onClick={() => setEditing(true)}>编辑</Button>
                <Button size="small" icon={<ReloadOutlined />} loading={isGenerating} onClick={handleRegenerate}>重新生成</Button>
                <Popconfirm title="确定删除此视频？" onConfirm={() => onDelete(video.id)}>
                  <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>
              </Space>
            )}
          </div>
        </div>

        {/* 右侧：设置区 */}
        <div className={styles.createRight}>
          {editing ? (
            <Form form={form} layout="vertical" size="small">
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
                <Text type="secondary" style={{ fontSize: 12 }}>标签</Text>
                <div style={{ marginTop: 4 }}>
                  <Space wrap>
                    {tags.length > 0 ? tags.map((t) => <Tag key={t}>{t}</Tag>) : <Text type="secondary">无</Text>}
                  </Space>
                </div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>模型</Text>
                <div style={{ marginTop: 4, fontSize: 13 }}>{video.modelName || '未知'}</div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>尺寸</Text>
                <div style={{ marginTop: 4, fontSize: 13 }}>{video.width} x {video.height}</div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>帧数 / 帧率</Text>
                <div style={{ marginTop: 4, fontSize: 13 }}>{video.numFrames} 帧 / {video.frameRate} FPS</div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>时长</Text>
                <div style={{ marginTop: 4, fontSize: 13 }}>{formatDuration(video.duration)}</div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>创建时间</Text>
                <div style={{ marginTop: 4, fontSize: 13 }}>{fmtTime(video.createdAt)}</div>
              </div>
            </>
          )}
        </div>
      </div>
    </Modal>
  )
}
