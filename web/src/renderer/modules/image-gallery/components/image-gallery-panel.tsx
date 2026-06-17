/** 图片画廊主面板 */
import { useState, useCallback } from 'react'
import {
  Card, Tag, Button, Spin, Empty, App, Modal, Input, Select, Typography, Space,
} from 'antd'
import {
  PlusOutlined, DeleteOutlined, ReloadOutlined,
} from '@ant-design/icons'
import { useImageGallery } from '../hooks/use-image-gallery'
import type { ImageGallery, ImageGalleryFormInput, ImageGenerateInput } from '../types'
import { ImageCreateModal } from './image-create-modal'
import { ImageDetailModal } from './image-detail-modal'
import styles from './image-gallery.module.css'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'

const { Text } = Typography

/** 将本地路径转为 API URL */
function toImageUrl(filePath: string) {
  if (!filePath) return ''
  const filename = filePath.split(/[/\\]/).pop() || ''
  return `${API_BASE_URL}${API_PREFIX}/image_gallery/files/${encodeURIComponent(filename)}`
}

export default function ImageGalleryPanel() {
  const { message } = App.useApp()
  const {
    imagesQuery, tagsQuery,
    createImage, deleteImage, generateImage,
    isCreating, isGenerating,
  } = useImageGallery()

  const [tagFilter, setTagFilter] = useState<string | undefined>()
  const [page, setPage] = useState(1)
  const pageSize = 40

  const { data: imagesData, isLoading } = imagesQuery({ tag: tagFilter, page, pageSize })
  const { data: tags = [] } = tagsQuery()

  const images = imagesData?.items || []
  const total = imagesData?.total || 0

  // 创建弹窗
  const [createOpen, setCreateOpen] = useState(false)
  // 详情弹窗
  const [detailImage, setDetailImage] = useState<ImageGallery | null>(null)

  const handleCreate = useCallback(async (input: ImageGalleryFormInput) => {
    try {
      await createImage(input)
      message.success('已保存')
      setCreateOpen(false)
    } catch {
      message.error('保存失败')
    }
  }, [createImage, message])

  const handleGenerate = useCallback(async (input: ImageGenerateInput) => {
    return await generateImage(input)
  }, [generateImage])

  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteImage(id)
      message.success('已删除')
      setDetailImage(null)
    } catch {
      message.error('删除失败')
    }
  }, [deleteImage, message])

  return (
    <div className={styles.galleryContainer}>
      {/* 工具栏 */}
      <div className={styles.toolbar}>
        <div className={styles.tagBar}>
          <Tag
            color={!tagFilter ? 'blue' : undefined}
            style={{ cursor: 'pointer' }}
            onClick={() => setTagFilter(undefined)}
          >
            全部
          </Tag>
          {tags.map((t) => (
            <Tag
              key={t}
              color={tagFilter === t ? 'blue' : undefined}
              style={{ cursor: 'pointer' }}
              onClick={() => setTagFilter(t)}
            >
              {t}
            </Tag>
          ))}
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          新增图片
        </Button>
      </div>

      {/* 瀑布流 */}
      {isLoading ? (
        <div className={styles.loadingWrap}>
          <Spin size="large" />
        </div>
      ) : images.length === 0 ? (
        <div className={styles.emptyWrap}>
          <Empty description="还没有图片，点击上方按钮生成吧" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      ) : (
        <div className={styles.masonry}>
          <div className={styles.masonryInner}>
            {images.map((img) => (
              <div
                key={img.id}
                className={styles.masonryItem}
                onClick={() => setDetailImage(img)}
              >
                <img
                  src={toImageUrl(img.filePath || (img as any).file_path)}
                  alt={img.name}
                  loading="lazy"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none'
                  }}
                />
                <div className={styles.masonryItemInfo}>
                  <div className={styles.masonryItemName}>{img.name}</div>
                  {img.tags && (
                    <div className={styles.masonryItemTags}>
                      {img.tags.split(',').filter(Boolean).map((t) => (
                        <Tag key={t} size="small">{t}</Tag>
                      ))}
                    </div>
                  )}
                  <div className={styles.masonryItemMeta}>
                    <span>{img.width}x{img.height}</span>
                    <span>{img.modelName?.split('/').pop()}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 分页 */}
      {total > pageSize && (
        <div className={styles.pagination}>
          <Button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            上一页
          </Button>
          <Text style={{ margin: '0 16px' }}>
            第 {page} 页 / 共 {Math.ceil(total / pageSize)} 页
          </Text>
          <Button
            disabled={page >= Math.ceil(total / pageSize)}
            onClick={() => setPage((p) => p + 1)}
          >
            下一页
          </Button>
        </div>
      )}

      {/* 新增弹窗 */}
      <ImageCreateModal
        open={createOpen}
        onOk={handleCreate}
        onGenerate={handleGenerate}
        isGenerating={isGenerating}
        onCancel={() => setCreateOpen(false)}
      />

      {/* 详情弹窗 */}
      <ImageDetailModal
        image={detailImage}
        allImages={images}
        onClose={() => setDetailImage(null)}
        onDelete={handleDelete}
        onRegenerate={handleGenerate}
        isGenerating={isGenerating}
      />
    </div>
  )
}
