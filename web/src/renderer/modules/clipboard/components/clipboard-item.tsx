import { useCallback, type MouseEvent } from 'react'
import { Tooltip } from 'antd'
import { formatRelativeTime } from '@/utils'
import { cn } from '@/utils'
import type { ClipboardItem } from '../types/clipboard'
import { getContentTypeIcon } from '../hooks/use-clipboard'
import styles from './clipboard-panel.module.css'

interface ClipboardItemProps {
  item: ClipboardItem
  /** 高亮后的内容 HTML（搜索匹配词高亮） */
  highlightedContent: string
  onCopy: (item: ClipboardItem) => void
  onContextMenu: (item: ClipboardItem, position: { x: number; y: number }) => void
  onOpenDetail: (item: ClipboardItem) => void
}

/**
 * 单条剪贴板列表项
 * 简洁展示：类型图标 + 内容预览 + 时间 + 固定标记
 */
export function ClipboardItemRow({
  item,
  highlightedContent,
  onCopy,
  onContextMenu,
  onOpenDetail,
}: ClipboardItemProps) {
  const handleClick = useCallback(() => {
    onCopy(item)
  }, [item, onCopy])

  const handleContext = useCallback(
    (e: MouseEvent) => {
      e.preventDefault()
      onContextMenu(item, { x: e.clientX, y: e.clientY })
    },
    [item, onContextMenu]
  )

  const handleDetailClick = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation()
      onOpenDetail(item)
    },
    [item, onOpenDetail]
  )

  const icon = getContentTypeIcon(item.contentType)

  return (
    <div
      className={cn(styles.clipboardItem, item.isPinned && styles.pinned)}
      onClick={handleClick}
      onContextMenu={handleContext}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter') handleClick()
      }}
    >
      <div className={styles.itemHeader}>
        <span className={styles.itemIcon}>{icon}</span>
        {item.language && <span className={styles.itemLanguage}>{item.language}</span>}
        {item.isPinned && (
          <Tooltip title="已固定">
            <span className={styles.pinBadge}>📌</span>
          </Tooltip>
        )}
        <span className={styles.itemTime}>{formatRelativeTime(item.copiedAt)}</span>
      </div>

      <div
        className={styles.itemContent}
        dangerouslySetInnerHTML={{ __html: highlightedContent }}
      />

      <div className={styles.itemActions}>
        <Tooltip title="查看详情">
          <button className={styles.actionBtn} onClick={handleDetailClick} aria-label="查看详情">
            👁️
          </button>
        </Tooltip>
      </div>
    </div>
  )
}
