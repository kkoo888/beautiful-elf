import { useEffect, useRef } from 'react'
import type { ClipboardItem } from '../types/clipboard'
import styles from './clipboard-panel.module.css'

interface ClipboardContextMenuProps {
  item: ClipboardItem | null
  position: { x: number; y: number } | null
  onClose: () => void
  onCopy: (item: ClipboardItem) => void
  onTogglePin: (id: string) => void
  onDelete: (id: string) => void
  onOpenDetail: (item: ClipboardItem) => void
}

/**
 * 剪贴板右键菜单
 * 支持：复制、固定/取消固定、查看详情、删除
 */
export function ClipboardContextMenu({
  item,
  position,
  onClose,
  onCopy,
  onTogglePin,
  onDelete,
  onOpenDetail,
}: ClipboardContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭
  useEffect(() => {
    if (!item || !position) return

    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [item, position, onClose])

  if (!item || !position) return null

  const menuItems = [
    {
      key: 'copy',
      label: '📋 复制',
      onClick: () => {
        onCopy(item)
        onClose()
      },
    },
    {
      key: 'detail',
      label: '👁️ 查看详情',
      onClick: () => {
        onOpenDetail(item)
        onClose()
      },
    },
    {
      key: 'pin',
      label: item.isPinned ? '📌 取消固定' : '📌 固定',
      onClick: () => {
        onTogglePin(item.id)
        onClose()
      },
    },
    { key: 'divider', label: '', isDivider: true },
    {
      key: 'delete',
      label: '🗑️ 删除',
      danger: true,
      onClick: () => {
        onDelete(item.id)
        onClose()
      },
    },
  ]

  return (
    <div
      ref={menuRef}
      className={styles.contextMenu}
      style={{
        left: position.x,
        top: position.y,
      }}
      role="menu"
    >
      {menuItems.map((mi) =>
        mi.isDivider ? (
          <div key={mi.key} className={styles.contextMenuDivider} />
        ) : (
          <button
            key={mi.key}
            className={`${styles.contextMenuItem} ${mi.danger ? styles.danger : ''}`}
            onClick={mi.onClick}
            role="menuitem"
          >
            {mi.label}
          </button>
        )
      )}
    </div>
  )
}
