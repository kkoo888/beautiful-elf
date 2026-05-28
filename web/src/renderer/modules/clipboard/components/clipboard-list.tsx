import { useRef, useCallback, useEffect } from 'react'
import { FixedSizeList as VirtualList } from 'react-window'
import { Empty, Spin } from 'antd'
import type { ClipboardItem } from '../types/clipboard'
import { ClipboardItemRow } from './clipboard-item'
import styles from './clipboard-panel.module.css'

interface ClipboardListProps {
  items: ClipboardItem[]
  loading: boolean
  getHighlightedContent: (content: string) => string
  onCopy: (item: ClipboardItem) => void
  onContextMenu: (
    item: ClipboardItem,
    position: { x: number; y: number }
  ) => void
  onOpenDetail: (item: ClipboardItem) => void
  onLoadMore: () => void
}

/** 列表项高度（px） */
const ITEM_HEIGHT = 80

/**
 * 剪贴板历史列表
 * 使用 react-window 虚拟滚动，支持上千条数据
 */
export function ClipboardList({
  items,
  loading,
  getHighlightedContent,
  onCopy,
  onContextMenu,
  onOpenDetail,
  onLoadMore
}: ClipboardListProps) {
  const listRef = useRef<VirtualList>(null)

  // 滚动到底部时触发加载更多
  const handleItemsRendered = useCallback(
    ({
      visibleStopIndex
    }: {
      visibleStartIndex: number
      visibleStopIndex: number
    }) => {
      if (visibleStopIndex >= items.length - 5) {
        onLoadMore()
      }
    },
    [items.length, onLoadMore]
  )

  // 列表更新时重置滚动位置
  useEffect(() => {
    listRef.current?.scrollToItem(0, 'start')
  }, [items.length > 0 && items[0]?.id])

  if (!loading && items.length === 0) {
    return (
      <div className={styles.emptyState}>
        <Empty
          description="复制内容会自动记录在这里 📋"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </div>
    )
  }

  return (
    <div className={styles.listContainer}>
      {loading && items.length === 0 ? (
        <div className={styles.loadingState}>
          <Spin tip="加载中..." />
        </div>
      ) : (
        <VirtualList
          ref={listRef}
          height={600}
          width="100%"
          itemCount={items.length}
          itemSize={ITEM_HEIGHT}
          itemData={items}
          onItemsRendered={handleItemsRendered}
          className={styles.virtualList}
        >
          {({ index, style }) => {
            const item = items[index]
            return (
              <div style={style}>
                <ClipboardItemRow
                  item={item}
                  highlightedContent={getHighlightedContent(item.content)}
                  onCopy={onCopy}
                  onContextMenu={onContextMenu}
                  onOpenDetail={onOpenDetail}
                />
              </div>
            )
          }}
        </VirtualList>
      )}

      {loading && items.length > 0 && (
        <div className={styles.loadMore}>
          <Spin size="small" />
        </div>
      )}
    </div>
  )
}
