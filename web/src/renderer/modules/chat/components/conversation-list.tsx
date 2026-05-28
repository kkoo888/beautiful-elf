/**
 * 会话列表侧栏组件
 * 支持搜索、新建、删除、虚拟滚动
 */

import React, { useState, useMemo, useCallback, useRef } from 'react'
import { Button, Input, Popconfirm, Empty, Tooltip } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { FixedSizeList as VirtualList } from 'react-window'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import type { Conversation } from '../types/chat'
import styles from './conversation-list.module.css'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

interface ConversationListProps {
  /** 会话列表 */
  conversations: Conversation[]
  /** 当前会话 ID */
  currentId: string | null
  /** 新建会话 */
  onCreate: () => void
  /** 切换会话 */
  onSwitch: (id: string) => void
  /** 删除会话 */
  onDelete: (id: string) => void
}

const ITEM_HEIGHT = 72
const VIRTUAL_THRESHOLD = 50

/** 格式化时间 */
function formatTime(ts: number): string {
  const d = dayjs(ts)
  const now = dayjs()
  if (d.isSame(now, 'day')) return d.format('HH:mm')
  if (d.isSame(now.subtract(1, 'day'), 'day')) return '昨天'
  if (d.isSame(now, 'year')) return d.format('M月D日')
  return d.format('YY/M/D')
}

/** 单条会话项 */
const ConversationItem: React.FC<{
  conv: Conversation
  isActive: boolean
  onSwitch: (id: string) => void
  onDelete: (id: string) => void
}> = React.memo(({ conv, isActive, onSwitch, onDelete }) => (
  <div
    className={`${styles.item} ${isActive ? styles.itemActive : ''}`}
    onClick={() => onSwitch(conv.id)}
    role="button"
    tabIndex={0}
    onKeyDown={(e) => {
      if (e.key === 'Enter' || e.key === ' ') onSwitch(conv.id)
    }}
  >
    <div className={styles.itemContent}>
      <div className={styles.itemTitle}>{conv.title}</div>
      {conv.lastMessage && (
        <div className={styles.itemPreview}>{conv.lastMessage}</div>
      )}
    </div>
    <div className={styles.itemMeta}>
      <span className={styles.itemTime}>{formatTime(conv.updatedAt)}</span>
      <Popconfirm
        title="确定删除此会话？"
        description="删除后不可恢复"
        onConfirm={(e) => {
          e?.stopPropagation()
          onDelete(conv.id)
        }}
        onCancel={(e) => e?.stopPropagation()}
        okText="删除"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <Button
          type="text"
          size="small"
          icon={<DeleteOutlined />}
          className={styles.deleteBtn}
          onClick={(e) => e.stopPropagation()}
        />
      </Popconfirm>
    </div>
  </div>
))
ConversationItem.displayName = 'ConversationItem'

/** 虚拟列表行渲染 */
const VirtualRow: React.FC<{
  index: number
  style: React.CSSProperties
  data: {
    items: Conversation[]
    currentId: string | null
    onSwitch: (id: string) => void
    onDelete: (id: string) => void
  }
}> = ({ index, style, data }) => {
  const conv = data.items[index]
  return (
    <div style={style}>
      <ConversationItem
        conv={conv}
        isActive={conv.id === data.currentId}
        onSwitch={data.onSwitch}
        onDelete={data.onDelete}
      />
    </div>
  )
}

/** 防抖 hook */
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  React.useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

/** 会话列表组件 */
export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  currentId,
  onCreate,
  onSwitch,
  onDelete,
}) => {
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 200)
  const listRef = useRef<VirtualList>(null)

  const filtered = useMemo(() => {
    if (!debouncedSearch.trim()) return conversations
    const q = debouncedSearch.toLowerCase()
    return conversations.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.lastMessage?.toLowerCase().includes(q)
    )
  }, [conversations, debouncedSearch])

  const itemData = useMemo(
    () => ({ items: filtered, currentId, onSwitch, onDelete }),
    [filtered, currentId, onSwitch, onDelete]
  )

  const handleSearch = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value),
    []
  )

  const useVirtual = filtered.length > VIRTUAL_THRESHOLD

  return (
    <div className={styles.container}>
      {/* 顶部操作栏 */}
      <div className={styles.header}>
        <Tooltip title="新建会话">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={onCreate}
            className={styles.createBtn}
            block
          >
            新建会话
          </Button>
        </Tooltip>
      </div>

      {/* 搜索框 */}
      <div className={styles.searchWrap}>
        <Input
          placeholder="搜索会话…"
          value={search}
          onChange={handleSearch}
          allowClear
          size="small"
          className={styles.searchInput}
        />
      </div>

      {/* 会话列表 */}
      <div className={styles.listWrap}>
        {filtered.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={search ? '无匹配会话' : '暂无会话'}
            className={styles.empty}
          />
        ) : useVirtual ? (
          <VirtualList
            ref={listRef}
            height={600}
            itemCount={filtered.length}
            itemSize={ITEM_HEIGHT}
            width="100%"
            itemData={itemData}
          >
            {VirtualRow}
          </VirtualList>
        ) : (
          <div className={styles.list}>
            {filtered.map((conv) => (
              <ConversationItem
                key={conv.id}
                conv={conv}
                isActive={conv.id === currentId}
                onSwitch={onSwitch}
                onDelete={onDelete}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
