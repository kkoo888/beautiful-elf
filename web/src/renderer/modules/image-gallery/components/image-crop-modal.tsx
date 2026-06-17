/** 头像图片选择 + 裁剪弹窗 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { Modal, Button, Spin, App, Input } from 'antd'
import { useImageGallery } from '../hooks/use-image-gallery'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'
import styles from './image-gallery.module.css'

const CROP_SIZE = 80

function toImageUrl(filePath: string) {
  if (!filePath) return ''
  const filename = filePath.split(/[/\\]/).pop() || ''
  return `${API_BASE_URL}${API_PREFIX}/image_gallery/files/${encodeURIComponent(filename)}`
}

interface ImageCropModalProps {
  open: boolean
  onOk: (base64: string) => void
  onCancel: () => void
}

export function ImageCropModal({ open, onOk, onCancel }: ImageCropModalProps) {
  const { message } = App.useApp()
  const { imagesQuery } = useImageGallery()
  const { data, isLoading } = imagesQuery({ page: 1, pageSize: 100 })
  const images = data?.items || []

  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [croppedResult, setCroppedResult] = useState<string | null>(null)
  const [tagFilter, setTagFilter] = useState('')
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imgRef = useRef<HTMLImageElement | null>(null)

  useEffect(() => {
    if (open) {
      setSelectedImage(null)
      setCroppedResult(null)
      setTagFilter('')
    }
  }, [open])

  const handleSelect = useCallback((img: any) => {
    const url = toImageUrl(img.filePath || img.file_path)
    setSelectedImage(url)
    setCroppedResult(null)

    // 用 fetch 获取 blob，避免 Canvas 跨域污染
    fetch(url)
      .then((res) => res.blob())
      .then((blob) => {
        const blobUrl = URL.createObjectURL(blob)
        const imgEl = new Image()
        imgEl.onload = () => {
          imgRef.current = imgEl
          const canvas = canvasRef.current
          if (!canvas) return
          const ctx = canvas.getContext('2d')
          if (!ctx) return

          canvas.width = CROP_SIZE
          canvas.height = CROP_SIZE

          const scale = Math.max(CROP_SIZE / imgEl.width, CROP_SIZE / imgEl.height)
          const sw = CROP_SIZE / scale
          const sh = CROP_SIZE / scale
          const sx = (imgEl.width - sw) / 2
          const sy = (imgEl.height - sh) / 2

          ctx.clearRect(0, 0, CROP_SIZE, CROP_SIZE)
          ctx.drawImage(imgEl, sx, sy, sw, sh, 0, 0, CROP_SIZE, CROP_SIZE)
          setCroppedResult(canvas.toDataURL('image/png'))
          URL.revokeObjectURL(blobUrl)
        }
        imgEl.src = blobUrl
      })
      .catch(() => {})
  }, [])

  const handleOk = useCallback(() => {
    if (!croppedResult) {
      message.warning('请先选择一张图片')
      return
    }
    onOk(croppedResult)
    message.success('头像已设置')
  }, [croppedResult, onOk, message])

  const filteredImages = tagFilter
    ? images.filter((i) => (i.tags || '').split(',').includes(tagFilter))
    : images

  const allTags = [...new Set(images.flatMap((i) => (i.tags || '').split(',').filter(Boolean)))]

  return (
    <Modal
      open={open}
      title="选择头像图片"
      width={700}
      onOk={handleOk}
      onCancel={onCancel}
      okText="确认"
      cancelText="取消"
      okButtonProps={{ disabled: !croppedResult }}
    >
      <div style={{ display: 'flex', gap: 20 }}>
        {/* 左侧：图片网格 */}
        <div style={{ flex: 1, maxHeight: 400, overflowY: 'auto' }}>
          {allTags.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <Space wrap size={[0, 4]}>
                <Tag
                  size="small"
                  style={{ cursor: 'pointer' }}
                  color={!tagFilter ? 'blue' : undefined}
                  onClick={() => setTagFilter('')}
                >
                  全部
                </Tag>
                {allTags.map((t) => (
                  <Tag
                    key={t}
                    size="small"
                    style={{ cursor: 'pointer' }}
                    color={tagFilter === t ? 'blue' : undefined}
                    onClick={() => setTagFilter(t)}
                  >
                    {t}
                  </Tag>
                ))}
              </Space>
            </div>
          )}
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
          ) : filteredImages.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无图片</div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
              {filteredImages.map((img) => {
                const url = toImageUrl(img.filePath || (img as any).file_path)
                const isSelected = selectedImage === url
                return (
                  <div
                    key={img.id}
                    onClick={() => handleSelect(img)}
                    style={{
                      cursor: 'pointer',
                      borderRadius: 6,
                      overflow: 'hidden',
                      border: isSelected ? '2px solid #1677ff' : '2px solid transparent',
                      transition: 'border-color 0.2s',
                    }}
                  >
                    <img
                      src={url}
                      alt={img.name}
                      style={{ width: '100%', aspectRatio: '1', objectFit: 'cover', display: 'block' }}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                    />
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* 右侧：裁剪预览 */}
        <div style={{ width: 160, textAlign: 'center' }}>
          <div style={{ marginBottom: 8, fontSize: 12, color: '#666' }}>裁剪预览 ({CROP_SIZE}x{CROP_SIZE})</div>
          <div style={{
            width: CROP_SIZE, height: CROP_SIZE, margin: '0 auto',
            borderRadius: '50%', overflow: 'hidden',
            border: '2px solid #d9d9d9', background: '#fafafa',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {croppedResult ? (
              <img src={croppedResult} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <span style={{ color: '#ccc', fontSize: 11 }}>选择图片</span>
            )}
          </div>
          <canvas ref={canvasRef} style={{ display: 'none' }} />
        </div>
      </div>
    </Modal>
  )
}

// 需要 Tag 组件
import { Tag, Space } from 'antd'
