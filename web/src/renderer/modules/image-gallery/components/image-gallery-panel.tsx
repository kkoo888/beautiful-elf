/** 图片画廊主面板 */
import { useState, useCallback, useRef, useEffect } from 'react'
import {
  Tag, Button, Spin, Empty, App, Space,
} from 'antd'
import {
  PlusOutlined, PictureOutlined,
} from '@ant-design/icons'
import { useImageGallery } from '../hooks/use-image-gallery'
import { fetchImages } from '../services/image-gallery-api'
import type { ImageGallery, ImageGalleryFormInput, ImageGenerateInput, ImageImg2ImgInput } from '../types'
import { ImageCreateModal } from './image-create-modal'
import { ImageDetailModal } from './image-detail-modal'
import { ImageImg2ImgModal } from './image-img2img-modal'
import styles from './image-gallery.module.css'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'

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
    createImage, deleteImage, generateImage, generateImageImg2Img,
    isCreating, isGenerating, isImg2Imging,
  } = useImageGallery()

  const [tagFilter, setTagFilter] = useState<string | undefined>()
  const [images, setImages] = useState<ImageGallery[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loadingMore, setLoadingMore] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const pageSize = 40
  const hasMore = images.length < total
  const sentinelRef = useRef<HTMLDivElement>(null)

  // 加载数据（追加模式）
  const loadPage = useCallback(async (p: number, append: boolean) => {
    try {
      const { items, total: t } = await fetchImages({ tag: tagFilter, page: p, pageSize })
      setImages((prev) => append ? [...prev, ...items] : items)
      setTotal(t)
    } catch {
      // silent
    } finally {
      setInitialLoading(false)
      setLoadingMore(false)
    }
  }, [tagFilter])

  // tag 变化时重置
  useEffect(() => {
    setImages([])
    setTotal(0)
    setPage(1)
    setInitialLoading(true)
    loadPage(1, false)
  }, [tagFilter, loadPage])

  // 加载下一页
  useEffect(() => {
    if (page > 1) loadPage(page, true)
  }, [page, loadPage])

  // IntersectionObserver 监听哨兵元素
  useEffect(() => {
    const el = sentinelRef.current
    if (!el) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !initialLoading) {
          setLoadingMore(true)
          setPage((p) => p + 1)
        }
      },
      { threshold: 0.1 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [hasMore, loadingMore, initialLoading])

  // 创建弹窗
  const [createOpen, setCreateOpen] = useState(false)
  // 图生图弹窗
  const [img2ImgOpen, setImg2ImgOpen] = useState(false)
  // 详情弹窗
  const [detailImage, setDetailImage] = useState<ImageGallery | null>(null)

  const { data: tags = [] } = tagsQuery()

  const reload = useCallback(() => {
    setImages([])
    setTotal(0)
    setPage(1)
    setInitialLoading(true)
    loadPage(1, false)
  }, [loadPage])

  const handleCreate = useCallback(async (input: ImageGalleryFormInput) => {
    try {
      await createImage(input)
      message.success('已保存')
      setCreateOpen(false)
      reload()
    } catch {
      message.error('保存失败')
    }
  }, [createImage, message, reload])

  const handleGenerate = useCallback(async (input: ImageGenerateInput) => {
    return await generateImage(input)
  }, [generateImage])

  const handleImg2Img = useCallback(async (input: ImageImg2ImgInput) => {
    return await generateImageImg2Img(input)
  }, [generateImageImg2Img])

  const handleSaveImg2Img = useCallback(async (input: ImageGalleryFormInput) => {
    await createImage(input)
  }, [createImage])

  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteImage(id)
      message.success('已删除')
      setDetailImage(null)
      reload()
    } catch {
      message.error('删除失败')
    }
  }, [deleteImage, message, reload])

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
        <Space>
          <Button icon={<PictureOutlined />} onClick={() => setImg2ImgOpen(true)}>
            图生图
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            新增图片
          </Button>
        </Space>
      </div>

      {/* 瀑布流 */}
      {initialLoading ? (
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
          {/* 无限滚动哨兵 */}
          <div ref={sentinelRef} style={{ height: 1 }} />
          {loadingMore && (
            <div style={{ textAlign: 'center', padding: '12px 0' }}>
              <Spin />
            </div>
          )}
          {!hasMore && images.length > 0 && (
            <div style={{ textAlign: 'center', padding: '12px 0', color: '#999', fontSize: 12 }}>
              已加载全部
            </div>
          )}
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

      {/* 图生图弹窗 */}
      <ImageImg2ImgModal
        open={img2ImgOpen}
        onOk={handleImg2Img}
        onSave={handleSaveImg2Img}
        isGenerating={isImg2Imging}
        onCancel={() => setImg2ImgOpen(false)}
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
