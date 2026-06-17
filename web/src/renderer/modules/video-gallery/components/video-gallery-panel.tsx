/** 视频画廊主面板 */
import { useState, useCallback } from 'react'
import {
  Card, Tag, Button, Spin, Empty, App, Modal, Input, Select, Typography, Space,
} from 'antd'
import {
  PlusOutlined, DeleteOutlined, ReloadOutlined, PlayCircleOutlined,
} from '@ant-design/icons'
import { useVideoGallery } from '../hooks/use-video-gallery'
import type { VideoGallery, VideoGalleryFormInput, VideoGenerateInput } from '../types'
import { VideoCreateModal } from './video-create-modal'
import { VideoDetailModal } from './video-detail-modal'
import styles from './video-gallery.module.css'
import { API_BASE_URL, API_PREFIX } from '@shared/constants'

const { Text } = Typography

/** 将本地路径转为 API URL */
function toVideoUrl(filePath: string) {
  if (!filePath) return ''
  const filename = filePath.split(/[/\\]/).pop() || ''
  return `${API_BASE_URL}${API_PREFIX}/video_gallery/files/${encodeURIComponent(filename)}`
}

function formatDuration(seconds: number) {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`
}

export default function VideoGalleryPanel() {
  const { message } = App.useApp()
  const {
    videosQuery, tagsQuery,
    createVideo, deleteVideo, generateVideo,
    isCreating, isGenerating,
  } = useVideoGallery()

  const [tagFilter, setTagFilter] = useState<string | undefined>()
  const [page, setPage] = useState(1)
  const pageSize = 40

  const { data: videosData, isLoading } = videosQuery({ tag: tagFilter, page, pageSize })
  const { data: tags = [] } = tagsQuery()

  const videos = videosData?.items || []
  const total = videosData?.total || 0

  const [createOpen, setCreateOpen] = useState(false)
  const [detailVideo, setDetailVideo] = useState<VideoGallery | null>(null)

  const handleCreate = useCallback(async (input: VideoGalleryFormInput) => {
    try {
      await createVideo(input)
      message.success('已保存')
      setCreateOpen(false)
    } catch {
      message.error('保存失败')
    }
  }, [createVideo, message])

  const handleGenerate = useCallback(async (input: VideoGenerateInput) => {
    return await generateVideo(input)
  }, [generateVideo])

  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteVideo(id)
      message.success('已删除')
      setDetailVideo(null)
    } catch {
      message.error('删除失败')
    }
  }, [deleteVideo, message])

  return (
    <div className={styles.videoGalleryContainer}>
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
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            新增视频
          </Button>
        </Space>
      </div>

      {/* 瀑布流 */}
      {isLoading ? (
        <div className={styles.loadingWrap}>
          <Spin size="large" />
        </div>
      ) : videos.length === 0 ? (
        <div className={styles.emptyWrap}>
          <Empty description="还没有视频，点击上方按钮生成吧" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      ) : (
        <div className={styles.masonry}>
          <div className={styles.masonryInner}>
            {videos.map((vid) => (
              <div
                key={vid.id}
                className={styles.masonryItem}
                onClick={() => setDetailVideo(vid)}
              >
                <video
                  src={toVideoUrl(vid.filePath || (vid as any).file_path)}
                  className={styles.masonryItemVideo}
                  muted
                  preload="metadata"
                  onMouseEnter={(e) => (e.target as HTMLVideoElement).play()}
                  onMouseLeave={(e) => {
                    const v = e.target as HTMLVideoElement
                    v.pause()
                    v.currentTime = 0
                  }}
                />
                <div className={styles.masonryItemInfo}>
                  <div className={styles.masonryItemName}>{vid.name}</div>
                  {vid.tags && (
                    <div className={styles.masonryItemTags}>
                      {vid.tags.split(',').filter(Boolean).map((t) => (
                        <Tag key={t} size="small">{t}</Tag>
                      ))}
                    </div>
                  )}
                  <div className={styles.masonryItemMeta}>
                    <span>{vid.width}x{vid.height}</span>
                    <span>{formatDuration(vid.duration)}</span>
                    <span>{vid.modelName?.split('/').pop()}</span>
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
      <VideoCreateModal
        open={createOpen}
        onOk={handleCreate}
        onGenerate={handleGenerate}
        isGenerating={isGenerating}
        onCancel={() => setCreateOpen(false)}
      />

      {/* 详情弹窗 */}
      <VideoDetailModal
        video={detailVideo}
        allVideos={videos}
        onClose={() => setDetailVideo(null)}
        onDelete={handleDelete}
        onRegenerate={handleGenerate}
        isGenerating={isGenerating}
      />
    </div>
  )
}
