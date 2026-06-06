import { Typography, Badge } from 'antd'
import { useClipboard } from '../hooks/use-clipboard'
import { ClipboardSearch } from './clipboard-search'
import { ClipboardList } from './clipboard-list'
import { ClipboardDetail } from './clipboard-detail'
import { ClipboardContextMenu } from './clipboard-context-menu'
import styles from './clipboard-panel.module.css'

const { Title } = Typography

/**
 * 剪贴板主面板
 * 整合搜索、虚拟滚动列表、详情抽屉、右键菜单
 */
export function ClipboardPanel() {
  const {
    items,
    filteredItems,
    loading,
    keyword,
    detailItem,
    contextMenuItem,
    contextMenuPosition,
    setKeyword,
    copyToClipboard,
    handleDelete,
    handleTogglePin,
    openDetail,
    closeDetail,
    openContextMenu,
    closeContextMenu,
    loadMore,
    getHighlightedContent,
  } = useClipboard()

  const pinnedCount = items.filter((i) => i.isPinned).length

  return (
    <div className={styles.panel}>
      {/* 标题栏 */}
      <div className={styles.panelHeader}>
        <Title level={4} className={styles.panelTitle}>
          <span className={styles.panelTitleIcon}>📋</span>
          剪贴板
          <span className={styles.panelCount}>
            {items.length > 0 && (
              <Badge
                count={items.length}
                showZero
                style={{ backgroundColor: '#fa8c16' }}
                overflowCount={999}
              />
            )}
          </span>
        </Title>
        {pinnedCount > 0 && (
          <span style={{ fontSize: 13, color: 'rgba(0,0,0,0.45)' }}>📌 {pinnedCount} 条固定</span>
        )}
      </div>

      {/* 搜索栏 */}
      <ClipboardSearch value={keyword} onChange={setKeyword} />

      {/* 列表 */}
      <ClipboardList
        items={filteredItems}
        loading={loading}
        getHighlightedContent={getHighlightedContent}
        onCopy={copyToClipboard}
        onContextMenu={openContextMenu}
        onOpenDetail={openDetail}
        onLoadMore={loadMore}
      />

      {/* 详情抽屉 */}
      <ClipboardDetail
        item={detailItem}
        onClose={closeDetail}
        onCopy={copyToClipboard}
        onTogglePin={handleTogglePin}
        onDelete={handleDelete}
      />

      {/* 右键菜单 */}
      <ClipboardContextMenu
        item={contextMenuItem}
        position={contextMenuPosition}
        onClose={closeContextMenu}
        onCopy={copyToClipboard}
        onTogglePin={handleTogglePin}
        onDelete={handleDelete}
        onOpenDetail={openDetail}
      />
    </div>
  )
}
