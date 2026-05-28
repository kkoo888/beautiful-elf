/**
 * 消息列表组件
 * 使用 react-window 虚拟滚动，支持 1000+ 消息不卡顿
 *
 * 优化点：
 * 1. 动态计算列表高度（ResizeObserver + window resize）
 * 2. 新消息自动滚到底部（仅在用户处于底部时）
 * 3. 滚动到顶部自动加载更多历史消息
 * 4. 加载历史消息时保持当前滚动位置不跳动
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FixedSizeList as VirtualList } from 'react-window'
import styles from './chat-panel.module.css'
import { MessageBubble } from './message-bubble'
import { ThinkingIndicator } from './thinking-indicator'
import type { ChatMessage, FeedbackData } from '../types/chat'

/** 消息行高（需要与实际渲染高度一致） */
const MESSAGE_ROW_HEIGHT = 120

/** 预渲染数量 */
const OVERSCAN_COUNT = 5

/** 触发加载更多的距离阈值（px） */
const LOAD_MORE_THRESHOLD = 200

/** 自动滚到底部的距离阈值（px） */
const AUTO_SCROLL_THRESHOLD = 150

interface MessageListProps {
  /** 消息列表 */
  messages: ChatMessage[]
  /** 是否正在加载 */
  isLoading: boolean
  /** 提交反馈回调 */
  onFeedback?: (data: FeedbackData) => Promise<void>
  /** 加载更多历史消息 */
  onLoadMore?: () => void
  /** 是否还有更多历史消息 */
  hasMore?: boolean
  /** 是否正在加载历史消息 */
  isLoadingMore?: boolean
}

/** 虚拟列表行组件 */
interface RowProps {
  index: number
  style: React.CSSProperties
  data: {
    messages: ChatMessage[]
    onFeedback?: (data: FeedbackData) => Promise<void>
  }
}

const Row: React.FC<RowProps> = React.memo(({ index, style, data }) => {
  const { messages, onFeedback } = data
  const message = messages[index]

  if (!message) return null

  return (
    <div style={style}>
      <MessageBubble message={message} onFeedback={onFeedback} />
    </div>
  )
})

Row.displayName = 'MessageRow'

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  onFeedback,
  onLoadMore,
  hasMore = false,
  isLoadingMore = false,
}) => {
  const listRef = useRef<VirtualList>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const outerRef = useRef<HTMLElement>(null)
  const [listHeight, setListHeight] = useState(600)

  // 追踪用户是否在底部附近
  const isNearBottomRef = useRef(true)
  // 加载前的滚动快照（用于保持位置）
  const scrollSnapshotRef = useRef<{ scrollOffset: number; scrollHeight: number } | null>(null)
  // 上一次消息数量（用于判断是追加还是前置）
  const prevCountRef = useRef(messages.length)
  // 防止重复触发加载
  const loadingMoreRef = useRef(false)

  // ---- 1. 动态计算列表高度 ----
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const updateHeight = (): void => {
      const rect = container.getBoundingClientRect()
      if (rect.height > 0) {
        setListHeight(rect.height)
      }
    }

    // 初始计算
    updateHeight()

    // 使用 ResizeObserver 监听容器尺寸变化
    const resizeObserver = new ResizeObserver(() => {
      updateHeight()
    })
    resizeObserver.observe(container)

    // 同时监听 window resize 作为 fallback
    window.addEventListener('resize', updateHeight)

    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', updateHeight)
    }
  }, [])

  // ---- 2. 滚动事件处理 ----
  const handleScroll = useCallback(
    ({ scrollOffset }: { scrollDirection: string; scrollOffset: number }) => {
      const el = outerRef.current
      if (!el) return

      const isNearBottom = el.scrollHeight - scrollOffset - el.clientHeight < AUTO_SCROLL_THRESHOLD
      isNearBottomRef.current = isNearBottom

      // 滚动到顶部附近时加载更多
      if (
        scrollOffset < LOAD_MORE_THRESHOLD &&
        hasMore &&
        !isLoadingMore &&
        !loadingMoreRef.current &&
        onLoadMore
      ) {
        loadingMoreRef.current = true

        // 快照当前滚动位置
        scrollSnapshotRef.current = {
          scrollOffset,
          scrollHeight: el.scrollHeight,
        }

        onLoadMore()
      }
    },
    [hasMore, isLoadingMore, onLoadMore]
  )

  // ---- 3. 新消息自动滚到底部 ----
  useEffect(() => {
    const newCount = messages.length
    const prevCount = prevCountRef.current

    if (newCount > prevCount && isNearBottomRef.current) {
      // 追加了新消息且用户在底部 → 自动滚动
      requestAnimationFrame(() => {
        listRef.current?.scrollToItem(newCount - 1, 'end')
      })
    }

    prevCountRef.current = newCount
  }, [messages.length])

  // ---- 4. 流式更新时滚动 ----
  useEffect(() => {
    if (isLoading && isNearBottomRef.current) {
      requestAnimationFrame(() => {
        listRef.current?.scrollToItem(messages.length - 1, 'end')
      })
    }
  }, [messages, isLoading])

  // ---- 5. 加载历史消息后恢复滚动位置 ----
  useEffect(() => {
    if (!isLoadingMore && scrollSnapshotRef.current) {
      const snapshot = scrollSnapshotRef.current
      scrollSnapshotRef.current = null
      loadingMoreRef.current = false

      // 等 DOM 更新后恢复位置
      requestAnimationFrame(() => {
        const el = outerRef.current
        if (!el) return

        const heightDiff = el.scrollHeight - snapshot.scrollHeight
        listRef.current?.scrollTo(snapshot.scrollOffset + heightDiff)
      })
    }
  }, [isLoadingMore, messages.length])

  // ---- 传递给虚拟行的数据 ----
  const itemData = useMemo(() => ({ messages, onFeedback }), [messages, onFeedback])

  // 空状态
  if (messages.length === 0 && !isLoading) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>💬</div>
        <div className={styles.emptyText}>开始对话吧</div>
        <div className={styles.emptySubtext}>输入你的问题，AI 助手会为你解答</div>
      </div>
    )
  }

  return (
    <div className={styles.virtualListContainer} ref={containerRef}>
      {/* 加载更多指示器 */}
      {isLoadingMore && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            zIndex: 5,
            display: 'flex',
            justifyContent: 'center',
            padding: '8px 0',
          }}
        >
          <ThinkingIndicator visible />
        </div>
      )}

      <VirtualList
        ref={listRef}
        height={listHeight}
        width="100%"
        itemCount={messages.length}
        itemSize={MESSAGE_ROW_HEIGHT}
        itemData={itemData}
        overscanCount={OVERSCAN_COUNT}
        onScroll={handleScroll}
        outerRef={outerRef}
        style={{ overflowX: 'hidden' }}
      >
        {Row}
      </VirtualList>

      {isLoading && <ThinkingIndicator visible />}
    </div>
  )
}

/**
 * 简化版消息列表（不使用虚拟滚动，用于消息较少的场景）
 * 使用 MutationObserver 实现自动滚动
 */
export const SimpleMessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  onFeedback,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const isAtBottomRef = useRef(true)

  // 检查是否在底部
  const checkAtBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < 100
  }, [])

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [])

  // 监听滚动
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const handleScroll = (): void => {
      isAtBottomRef.current = checkAtBottom()
    }
    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [checkAtBottom])

  // 新消息自动滚动
  useEffect(() => {
    if (isAtBottomRef.current) {
      requestAnimationFrame(scrollToBottom)
    }
  }, [messages, scrollToBottom])

  if (messages.length === 0) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>💬</div>
        <div className={styles.emptyText}>开始对话吧</div>
        <div className={styles.emptySubtext}>输入你的问题，AI 助手会为你解答</div>
      </div>
    )
  }

  return (
    <div className={styles.messageList} ref={containerRef}>
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} onFeedback={onFeedback} />
      ))}
      {isLoading && <ThinkingIndicator visible />}
    </div>
  )
}
